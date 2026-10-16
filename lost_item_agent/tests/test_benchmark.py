"""
tests/test_benchmark.py
-----------------------
Unit and integration tests for the benchmarking engine, CSV exporter,
and visualization chart generator.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from benchmark.evidence import build_decision_log, candidate_count_sensitivity
from benchmark.exporter import export_csv, pivot_metric, summarize
from benchmark.runner import BenchmarkRecord, BenchmarkRunner
from benchmark.scenarios import BenchmarkScenario, FAST_SCENARIOS, SCENARIOS
from visualization.chart_viz import (
    build_comparison_table,
    draw_bar_comparison,
    draw_boxplot,
    draw_scaling_lines,
    draw_success_rate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sample_results_df() -> pd.DataFrame:
    """Run a fast scenario benchmark once for testing exporters and charts."""
    tiny_scenario = BenchmarkScenario(
        name="Tiny-Test",
        map_mode="grid",
        rows=5,
        cols=5,
        obstacle_density=0.0,
        seed=42,
        num_trials=2,
        description="Fast test scenario",
    )
    runner = BenchmarkRunner([tiny_scenario])
    return runner.run_all()


# ---------------------------------------------------------------------------
# Test Benchmark Scenarios
# ---------------------------------------------------------------------------

class TestBenchmarkScenarios:
    def test_scenarios_non_empty(self):
        assert len(SCENARIOS) >= 4
        assert len(FAST_SCENARIOS) >= 1

    def test_scenario_properties(self):
        sc = BenchmarkScenario(
            name="Test",
            map_mode="grid",
            rows=6,
            cols=8,
            obstacle_density=0.15,
        )
        assert sc.grid_size == 48
        assert "Test" in sc.label
        assert "6×8" in sc.label

    def test_scenario_requires_positive_trial_count(self):
        with pytest.raises(ValueError, match="num_trials"):
            BenchmarkScenario(name="Invalid", num_trials=0)

    def test_grid_scenario_rejects_non_finite_density(self):
        with pytest.raises(ValueError, match="obstacle_density"):
            BenchmarkScenario(
                name="Invalid",
                obstacle_density=float("nan"),
            )


# ---------------------------------------------------------------------------
# Test Benchmark Runner
# ---------------------------------------------------------------------------

class TestBenchmarkRunner:
    def test_run_single_trial(self):
        scenario = BenchmarkScenario(
            name="Tiny-Open",
            map_mode="grid",
            rows=5,
            cols=5,
            obstacle_density=0.0,
            seed=1,
            num_trials=1,
        )
        runner = BenchmarkRunner([scenario])
        df = runner.run_all()

        assert not df.empty
        assert len(df) == 3  # 3 algorithms for 1 trial
        assert set(df["algorithm"]) == {"BFS", "Greedy", "A*"}
        assert all(df["success"])

    def test_required_columns_present(self, sample_results_df: pd.DataFrame):
        expected_cols = {
            "scenario_name",
            "map_mode",
            "grid_size",
            "obstacle_density",
            "algorithm",
            "trial",
            "start",
            "goal",
            "execution_time_ms",
            "nodes_expanded",
            "nodes_generated",
            "path_cost",
            "path_length",
            "success",
        }
        assert expected_cols.issubset(set(sample_results_df.columns))

    def test_fairness_identical_start_goal_per_trial(self, sample_results_df: pd.DataFrame):
        for scenario_name in sample_results_df["scenario_name"].unique():
            sc_df = sample_results_df[sample_results_df["scenario_name"] == scenario_name]
            for trial_num in sc_df["trial"].unique():
                trial_df = sc_df[sc_df["trial"] == trial_num]
                assert trial_df["start"].nunique() == 1, "Algorithms must start at identical location per trial"
                assert trial_df["goal"].nunique() == 1, "Algorithms must target identical location per trial"

    def test_reproducibility(self):
        scenario = BenchmarkScenario(
            name="Tiny-Open",
            map_mode="grid",
            rows=5,
            cols=5,
            obstacle_density=0.0,
            seed=99,
            num_trials=2,
        )
        df1 = BenchmarkRunner([scenario]).run_all()
        df2 = BenchmarkRunner([scenario]).run_all()

        assert df1["path_cost"].equals(df2["path_cost"])
        assert df1["nodes_expanded"].equals(df2["nodes_expanded"])
        assert df1["nodes_generated"].equals(df2["nodes_generated"])

    def test_campus_mode_benchmark(self):
        scenario = BenchmarkScenario(
            name="Campus-Test",
            map_mode="campus",
            seed=7,
            num_trials=2,
        )
        runner = BenchmarkRunner([scenario])
        df = runner.run_all()
        assert not df.empty
        assert (df["map_mode"] == "campus").all()
        assert (df["success"]).all()


# ---------------------------------------------------------------------------
# Test Benchmark Exporter
# ---------------------------------------------------------------------------

class TestBenchmarkExporter:
    def test_export_csv_creates_file(self, sample_results_df: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "subfolder" / "benchmark_test.csv"
            result_path = export_csv(sample_results_df, out_path)
            assert result_path.exists()
            assert result_path.stat().st_size > 0

            # Verify contents load back into pandas
            loaded_df = pd.read_csv(result_path)
            assert len(loaded_df) == len(sample_results_df)

    def test_export_csv_empty_raises(self):
        with pytest.raises(ValueError, match="Cannot export an empty DataFrame"):
            export_csv(pd.DataFrame(), "dummy.csv")

    def test_summarize_statistics(self, sample_results_df: pd.DataFrame):
        summary = summarize(sample_results_df)
        assert not summary.empty
        assert "mean_nodes_expanded" in summary.columns
        assert "mean_execution_time_ms" in summary.columns
        assert "success_rate" in summary.columns
        assert "mean_memory_peak_kib" in summary.columns

    def test_memory_footprint_is_measured(self, sample_results_df: pd.DataFrame):
        assert "memory_peak_kib" in sample_results_df.columns
        assert (sample_results_df["memory_peak_kib"] > 0).all()

    def test_candidate_count_sensitivity_is_repeatable(self):
        first = candidate_count_sensitivity((1, 2, 3))
        second = candidate_count_sensitivity((1, 2, 3))
        assert len(first) == 9
        assert first[["candidate_count", "algorithm", "total_nodes_expanded"]].equals(
            second[["candidate_count", "algorithm", "total_nodes_expanded"]]
        )

    def test_decision_log_includes_step_sequence(self):
        from environment.locations import build_default_campus
        from planner.candidate_planner import CandidatePlanner

        steps = CandidatePlanner(build_default_campus()).execute_mission(
            "Main Entrance", ["Reception"], "Reception"
        )
        log = build_decision_log("Main Entrance", "A*", steps)
        assert "| 1 | Main Entrance | Reception |" in log
        assert "Item recovered" in log

    def test_summary_keeps_failed_search_effort_but_excludes_failed_paths(self):
        df = pd.DataFrame([
            {
                "scenario_name": "Mixed",
                "map_mode": "grid",
                "grid_size": 25,
                "obstacle_density": 0.2,
                "algorithm": "A*",
                "success": True,
                "path_cost": 4.0,
                "path_length": 4,
                "nodes_expanded": 5,
                "nodes_generated": 7,
                "execution_time_ms": 1.0,
            },
            {
                "scenario_name": "Mixed",
                "map_mode": "grid",
                "grid_size": 25,
                "obstacle_density": 0.2,
                "algorithm": "A*",
                "success": False,
                "path_cost": float("nan"),
                "path_length": float("nan"),
                "nodes_expanded": 3,
                "nodes_generated": 4,
                "execution_time_ms": 3.0,
            },
        ])

        summary = summarize(df).iloc[0]

        assert summary["success_rate"] == 0.5
        assert summary["mean_path_cost"] == 4.0
        assert summary["mean_path_length"] == 4.0
        assert summary["mean_nodes_expanded"] == 4.0
        assert summary["mean_nodes_generated"] == 5.5
        assert summary["mean_execution_time_ms"] == 2.0
        assert summary["grid_size"] == 25

    def test_pivot_metric(self, sample_results_df: pd.DataFrame):
        summary = summarize(sample_results_df)
        pivot = pivot_metric(summary, "nodes_expanded", "mean")
        assert not pivot.empty
        for algo in ["BFS", "Greedy", "A*"]:
            assert algo in pivot.columns


# ---------------------------------------------------------------------------
# Test Visualization Charts
# ---------------------------------------------------------------------------

class TestVisualizationCharts:
    def test_draw_bar_comparison(self, sample_results_df: pd.DataFrame):
        summary = summarize(sample_results_df)
        fig = draw_bar_comparison(summary, "nodes_expanded")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_draw_scaling_lines(self, sample_results_df: pd.DataFrame):
        fig = draw_scaling_lines(sample_results_df, "nodes_expanded")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_scaling_chart_uses_numeric_grid_size(self):
        df = pd.DataFrame([
            {
                "scenario_name": "Large",
                "algorithm": "BFS",
                "grid_size": 900,
                "nodes_expanded": 90,
                "success": True,
            },
            {
                "scenario_name": "Small",
                "algorithm": "BFS",
                "grid_size": 25,
                "nodes_expanded": 10,
                "success": True,
            },
        ])
        summarized = summarize(df)
        fig = draw_scaling_lines(summarized, "nodes_expanded")

        assert list(fig.axes[0].lines[0].get_xdata()) == [25, 900]
        assert fig.axes[0].get_xlabel() == "Grid Size (cells)"
        plt.close(fig)

    def test_draw_boxplot(self, sample_results_df: pd.DataFrame):
        fig = draw_boxplot(sample_results_df, "execution_time_ms")
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_draw_success_rate(self, sample_results_df: pd.DataFrame):
        summary = summarize(sample_results_df)
        fig = draw_success_rate(summary)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_build_comparison_table(self, sample_results_df: pd.DataFrame):
        summary = summarize(sample_results_df)
        table = build_comparison_table(summary)
        assert isinstance(table, pd.DataFrame)
        assert not table.empty
        assert "Algorithm" in table.columns
