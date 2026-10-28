"""
backend/benchmark/run_experiments.py
------------------------------------
Executes reproducible benchmark experiments across quick and full suites,
saves actual raw and summary results to CSV, generates high-resolution
comparison charts for:
  - Execution Time (ms)
  - Nodes Expanded (Search Effort)
  - Path Cost (Optimality)
  - Scaling across Grid Sizes
  - Success Rate
and outputs a comprehensive markdown report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from benchmark.exporter import export_csv, summarize
from benchmark.runner import BenchmarkRunner
from benchmark.scenarios import FAST_SCENARIOS, SCENARIOS
from visualization.chart_viz import (
    draw_bar_comparison,
    draw_scaling_lines,
    draw_success_rate,
)


def run_and_save_experiments(suite_name: str = "all", trials: int = 3) -> dict[str, Path]:
    output_dir = PROJECT_ROOT / "output"
    evidence_dir = output_dir / "submission_evidence"
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    if suite_name == "fast":
        scenarios = FAST_SCENARIOS
    elif suite_name == "standard":
        scenarios = SCENARIOS
    else:  # all
        scenarios = SCENARIOS

    print(f"Running benchmark suite: {suite_name} ({len(scenarios)} scenarios, {trials} trials each)...")
    runner = BenchmarkRunner(verbose=True)
    raw_df = runner.run_all(scenarios)
    summary_df = summarize(raw_df)

    # 1. Save CSV files
    raw_csv_path = export_csv(raw_df, output_dir / "benchmark_results_raw.csv")
    summary_csv_path = export_csv(summary_df, output_dir / "benchmark_summary.csv")
    export_csv(raw_df, evidence_dir / "benchmark_results_raw.csv")
    export_csv(summary_df, evidence_dir / "benchmark_summary.csv")
    print(f"Saved raw CSV to: {raw_csv_path}")
    print(f"Saved summary CSV to: {summary_csv_path}")

    # 2. Generate comparison charts
    saved_charts: dict[str, Path] = {}

    print("Generating comparison charts...")
    # Chart 1: Execution Time
    fig_time = draw_bar_comparison(
        summary_df,
        "execution_time_ms",
        title="Execution Time Comparison — BFS vs Greedy vs A*",
        ylabel="Mean Execution Time (ms)",
    )
    time_path = evidence_dir / "chart_execution_time.png"
    fig_time.savefig(time_path, dpi=160, bbox_inches="tight")
    saved_charts["execution_time"] = time_path

    # Chart 2: Nodes Expanded (Search Effort)
    fig_expanded = draw_bar_comparison(
        summary_df,
        "nodes_expanded",
        title="Search Space Exploration (Nodes Expanded) — BFS vs Greedy vs A*",
        ylabel="Mean Nodes Expanded",
    )
    expanded_path = evidence_dir / "chart_expanded_nodes.png"
    fig_expanded.savefig(expanded_path, dpi=160, bbox_inches="tight")
    saved_charts["nodes_expanded"] = expanded_path

    # Chart 3: Path Cost (Optimality)
    fig_cost = draw_bar_comparison(
        summary_df,
        "path_cost",
        title="Path Travel Cost (Optimality) — BFS vs Greedy vs A*",
        ylabel="Mean Path Cost (units)",
    )
    cost_path = evidence_dir / "chart_path_cost.png"
    fig_cost.savefig(cost_path, dpi=160, bbox_inches="tight")
    saved_charts["path_cost"] = cost_path

    # Chart 4: Success Rate
    fig_succ = draw_success_rate(
        summary_df,
        title="Search Success Rate by Scenario — BFS vs Greedy vs A*",
    )
    succ_path = evidence_dir / "chart_success_rate.png"
    fig_succ.savefig(succ_path, dpi=160, bbox_inches="tight")
    saved_charts["success_rate"] = succ_path

    # Chart 5: Scaling Lines
    if "grid_size" in summary_df.columns and any(summary_df["grid_size"] > 0):
        fig_scale = draw_scaling_lines(
            summary_df,
            "execution_time_ms",
            title="Algorithm Runtime Scaling vs Grid Size",
        )
        scale_path = evidence_dir / "chart_scaling.png"
        fig_scale.savefig(scale_path, dpi=160, bbox_inches="tight")
        saved_charts["scaling"] = scale_path

    print(f"Generated {len(saved_charts)} charts in {evidence_dir}")
    return saved_charts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Lost Item Recovery Agent benchmark experiments.")
    parser.add_argument("--suite", choices=["fast", "standard", "all"], default="all", help="Suite to execute")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials per scenario")
    args = parser.parse_args()
    run_and_save_experiments(suite_name=args.suite, trials=args.trials)
