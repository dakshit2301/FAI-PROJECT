"""
app/components/benchmark_view.py
--------------------------------
Experimental benchmarking interface for empirical AI evaluation.
"""

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from benchmark.evidence import candidate_count_sensitivity
from benchmark.exporter import summarize
from benchmark.runner import BenchmarkRunner
from benchmark.scenarios import (
    BenchmarkScenario,
    FAST_SCENARIOS,
    SCENARIOS,
)
from visualization.chart_viz import (
    build_comparison_table,
    draw_bar_comparison,
    draw_boxplot,
    draw_scaling_lines,
    draw_success_rate,
)


def render_benchmark_page():
    """
    Renders the benchmark control panel, live evaluation runner, charts, and CSV download.
    """
    st.header("Benchmarks")
    st.markdown(
        "Compare BFS, Greedy Best-First Search, and A* across the available maps "
        "using the same start and goal for each trial."
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        suite_type = st.radio(
            "Scenario set",
            options=["Standard Suite (6 Scenarios)", "Fast CI Suite (3 Scenarios)", "Custom Grid Experiment"],
            index=1,
            help="The standard suite includes 5×5 to 50×50 grids and the campus map.",
        )

    with col2:
        seed = st.number_input("Seed", value=42, min_value=1, max_value=99999, help="Reproduces map and start/goal sampling.")

    with col3:
        num_trials = st.slider("Trials per scenario", min_value=1, max_value=10, value=3)

    # Custom experiment options
    custom_scenarios = None
    if suite_type == "Custom Grid Experiment":
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            c_rows = st.slider("Grid Rows", 5, 40, 15)
            c_cols = st.slider("Grid Columns", 5, 40, 15)
        with col_b:
            c_density = st.slider("Obstacle Density", 0.0, 0.40, 0.20, step=0.05)
        with col_c:
            c_name = st.text_input("Experiment Name", value="Custom-Run")

        custom_scenarios = [
            BenchmarkScenario(
                name=c_name,
                map_mode="grid",
                rows=c_rows,
                cols=c_cols,
                obstacle_density=c_density,
                seed=seed,
                num_trials=num_trials,
                description=f"{c_rows}x{c_cols} custom grid with {int(c_density*100)}% obstacles",
            )
        ]

    # Run Button
    run_btn = st.button("Run benchmarks", type="primary", use_container_width=True)

    if run_btn:
        # Determine scenarios to run
        if suite_type.startswith("Fast"):
            target_scenarios = [
                BenchmarkScenario(
                    name=s.name,
                    map_mode=s.map_mode,
                    rows=s.rows,
                    cols=s.cols,
                    obstacle_density=s.obstacle_density,
                    seed=seed,
                    num_trials=num_trials,
                    description=s.description,
                )
                for s in FAST_SCENARIOS
            ]
        elif suite_type.startswith("Standard"):
            target_scenarios = [
                BenchmarkScenario(
                    name=s.name,
                    map_mode=s.map_mode,
                    rows=s.rows,
                    cols=s.cols,
                    obstacle_density=s.obstacle_density,
                    seed=seed,
                    num_trials=num_trials,
                    description=s.description,
                )
                for s in SCENARIOS
            ]
        else:
            target_scenarios = custom_scenarios or []

        progress_bar = st.progress(0, text="Initializing benchmark runs...")
        runner = BenchmarkRunner(scenarios=target_scenarios, verbose=False)

        all_records = []
        total = len(target_scenarios)
        for idx, sc in enumerate(target_scenarios):
            progress_bar.progress((idx) / total, text=f"Executing scenario [{idx+1}/{total}]: {sc.name}...")
            recs = runner.run_scenario(sc)
            all_records.extend(recs)

        progress_bar.progress(1.0, text="Benchmark complete!")

        # Convert to DataFrame
        raw_df = pd.DataFrame([r.to_dict() for r in all_records])
        st.session_state["benchmark_df"] = raw_df

    # Display results if present in session state
    if "benchmark_df" in st.session_state and not st.session_state["benchmark_df"].empty:
        raw_df = st.session_state["benchmark_df"]
        summary_df = summarize(raw_df)

        st.success(
            f"Evaluated {len(raw_df)} algorithm runs across "
            f"{raw_df['scenario_name'].nunique()} scenarios."
        )

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Summary", "Charts", "Trial data", "CSV export", "Scalability evidence"
        ])

        with tab1:
            st.markdown("### Aggregated Benchmark Metrics")
            clean_table = build_comparison_table(summary_df)
            st.dataframe(clean_table, use_container_width=True, hide_index=True)

            st.caption(
                "Path cost and path length summarize successful trials only. Nodes expanded, nodes "
                "generated, and runtime include failed attempts; success rate counts all trials."
            )

        with tab2:
            st.markdown("### Empirical Performance Visualizations")

            metric_choice = st.selectbox(
                "Select Comparison Metric",
                options=["nodes_expanded", "execution_time_ms", "path_cost", "nodes_generated"],
                format_func=lambda x: {
                    "nodes_expanded": "Nodes Expanded (Search Space Explored)",
                    "execution_time_ms": "Execution Time (Wall-Clock ms)",
                    "path_cost": "Path Cost (Solution Distance)",
                    "nodes_generated": "Nodes Generated (Frontier Pushes)",
                }.get(x, x),
            )

            fig_bar = draw_bar_comparison(summary_df, metric=metric_choice)
            st.pyplot(fig_bar)
            plt.close(fig_bar)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("#### Scaling vs Grid Size")
                fig_scale = draw_scaling_lines(summary_df, metric=metric_choice)
                st.pyplot(fig_scale)
                plt.close(fig_scale)

            with col_c2:
                st.markdown("#### Metric Distribution (Box Plot)")
                fig_box = draw_boxplot(raw_df, metric=metric_choice)
                st.pyplot(fig_box)
                plt.close(fig_box)

            st.markdown("#### Overall Success Rate")
            fig_succ = draw_success_rate(summary_df)
            st.pyplot(fig_succ)
            plt.close(fig_succ)

        with tab3:
            st.markdown("### Granular Trial-by-Trial Data")
            st.dataframe(raw_df, use_container_width=True)

        with tab4:
            st.markdown("### Download benchmark data")
            csv_buffer = io.StringIO()
            raw_df.to_csv(csv_buffer, index=False)
            csv_str = csv_buffer.getvalue()

            st.download_button(
                label="Download raw trial data (CSV)",
                data=csv_str,
                file_name="lost_item_agent_benchmark_results.csv",
                mime="text/csv",
                type="primary",
            )

            sum_buffer = io.StringIO()
            summary_df.to_csv(sum_buffer, index=False)
            sum_str = sum_buffer.getvalue()

            st.download_button(
                label="Download summary data (CSV)",
                data=sum_str,
                file_name="lost_item_agent_benchmark_summary.csv",
                mime="text/csv",
            )

        with tab5:
            st.markdown("### Candidate-count sensitivity")
            st.caption(
                "Each algorithm plans the same deterministic campus candidate sets. "
                "This isolates the effect of candidate-set size on planning work."
            )
            sensitivity_df = candidate_count_sensitivity()
            st.dataframe(sensitivity_df, use_container_width=True, hide_index=True)
            st.line_chart(
                sensitivity_df.pivot(
                    index="candidate_count", columns="algorithm", values="total_nodes_expanded"
                )
            )
            sensitivity_csv = sensitivity_df.to_csv(index=False)
            st.download_button(
                label="Download candidate-count sensitivity (CSV)",
                data=sensitivity_csv,
                file_name="candidate_count_sensitivity.csv",
                mime="text/csv",
            )
    else:
        st.info("Run the selected scenarios to view metrics, charts, and CSV data.")
