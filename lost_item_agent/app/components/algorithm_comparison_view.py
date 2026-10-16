"""
app/components/algorithm_comparison_view.py
-------------------------------------------
Side-by-side evaluation of BFS, Greedy Best-First, and A* on identical search tasks.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from environment.graph import CampusGraph
from environment.grid import GridMap
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import euclidean_distance, manhattan_distance


def render_algorithm_comparison(
    graph_or_grid: CampusGraph | GridMap,
    start: str,
    goal: str,
    is_grid: bool = False,
):
    """
    Executes BFS, Greedy, and A* on the exact same problem instance and displays comparative analysis.
    """
    st.subheader(f"Route comparison: `{start}` → `{goal}`")

    # Select appropriate heuristic
    heuristic = manhattan_distance if is_grid else euclidean_distance
    # Run all three algorithms using high-precision timers
    res_bfs = bfs(graph_or_grid, start, goal)
    res_greedy = greedy_best_first(graph_or_grid, start, goal, heuristic)
    res_astar = astar(graph_or_grid, start, goal, heuristic)

    results = [res_bfs, res_greedy, res_astar]

    # Side-by-side metric cards
    col1, col2, col3 = st.columns(3)

    algo_cols = [col1, col2, col3]
    colors = ["#4C72B0", "#DD8452", "#55A868"]

    for col, res, color in zip(algo_cols, results, colors):
        with col:
            st.markdown(
                f"<div style='border-top: 4px solid {color}; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 6px;'>"
                f"<h4 style='margin:0; color:{color};'>{res.algorithm}</h4>"
                f"<p style='color:#A0AEC0; font-size:12px; margin-bottom:8px;'>Heuristic: {res.heuristic_used or 'None (Blind)'}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.write(f"**Status:** {'Success' if res.success else 'Failed'}")
            st.write(f"**Path Cost:** `{res.path_cost:.2f}`" if res.success else "**Path Cost:** `N/A`")
            st.write(f"**Path Hops:** `{res.path_length}`")
            st.write(f"**Nodes Expanded:** `{res.nodes_expanded}`")
            st.write(f"**Nodes Generated:** `{res.nodes_generated}`")
            st.write(f"**Runtime:** `{res.execution_time_ms:.3f} ms`")

            with st.expander("Show Path Sequence"):
                if res.success:
                    st.code(" → ".join(res.path))
                else:
                    st.write("No path found.")

    # Comparative Analysis Table
    st.markdown("#### Results")
    summary_data = {
        "Metric": [
            "Path Cost (Weighted)",
            "Path Length (Hops)",
            "Nodes Expanded",
            "Nodes Generated",
            "Execution Time (ms)",
            "Optimality Guarantee",
        ],
        "BFS": [
            f"{res_bfs.path_cost:.2f}" if res_bfs.success else "N/A",
            res_bfs.path_length,
            res_bfs.nodes_expanded,
            res_bfs.nodes_generated,
            f"{res_bfs.execution_time_ms:.3f}",
            "Hop-Optimal Only",
        ],
        "Greedy Best-First": [
            f"{res_greedy.path_cost:.2f}" if res_greedy.success else "N/A",
            res_greedy.path_length,
            res_greedy.nodes_expanded,
            res_greedy.nodes_generated,
            f"{res_greedy.execution_time_ms:.3f}",
            "Not Guaranteed",
        ],
        "A* Search": [
            f"{res_astar.path_cost:.2f}" if res_astar.success else "N/A",
            res_astar.path_length,
            res_astar.nodes_expanded,
            res_astar.nodes_generated,
            f"{res_astar.execution_time_ms:.3f}",
            "Cost-Optimal (Admissible h)",
        ],
    }
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    # Academic Findings Breakdown
    st.markdown("#### Comparison notes")
    obs = []
    if res_astar.success and res_bfs.success:
        if res_astar.path_cost < res_bfs.path_cost:
            obs.append(
                f"**Path cost:** A* found a lower cost path ({res_astar.path_cost:.1f}) than BFS ({res_bfs.path_cost:.1f}). "
                "This occurs because BFS optimizes hop count, ignoring weighted edge distances."
            )
        elif res_astar.path_cost == res_bfs.path_cost:
            obs.append(
                f"**Equal path cost:** A* and BFS returned identical path costs ({res_astar.path_cost:.1f})."
            )

    if res_greedy.success and res_astar.success:
        if res_greedy.path_cost > res_astar.path_cost:
            obs.append(
                f"**Greedy path cost:** Greedy Best-First found a path of cost "
                f"{res_greedy.path_cost:.1f} compared to A*'s {res_astar.path_cost:.1f}. "
                "Greedy minimizes estimated remaining cost h(n) greedily without accounting for past path cost g(n)."
            )
        if res_greedy.nodes_expanded < res_astar.nodes_expanded:
            obs.append(
                f"**Expanded nodes:** Greedy expanded fewer nodes ({res_greedy.nodes_expanded}) than A* ({res_astar.nodes_expanded}), "
                "demonstrating how purely goal-directed search can be faster when optimality is not required."
            )

    if not obs:
        if not all(result.success for result in results):
            obs.append(
                "At least one algorithm could not reach the goal; compare success "
                "status before interpreting path-cost metrics."
            )
        elif any(
            not math.isclose(results[0].path_cost, result.path_cost)
            for result in results[1:]
        ):
            obs.append(
                "The successful algorithms returned different path costs. Interpret "
                "the result using each algorithm's stated optimality guarantee."
            )
        else:
            obs.append(
                "All algorithms found a path with the same cost on this run; "
                "their explored-node counts and runtimes may still differ."
            )

    for o in obs:
        st.info(o)

    # Matplotlib Comparison Chart
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), facecolor="#FFFFFF")
    algos = ["BFS", "Greedy", "A*"]
    c_list = ["#4C72B0", "#DD8452", "#55A868"]

    # Chart 1: Path Cost
    costs = [r.path_cost if r.success else float("nan") for r in results]
    ax1 = axes[0]
    ax1.set_facecolor("#F7F9F6")
    bars1 = ax1.bar(algos, costs, color=c_list)
    ax1.set_title("Path Cost (successful runs)", color="#263B33", fontsize=10, fontweight="bold")
    ax1.tick_params(colors="#52665B")
    for b, result in zip(bars1, results):
        label = f"{result.path_cost:.1f}" if result.success else "N/A"
        y = b.get_height() + 0.1 if result.success else 0.1
        ax1.text(
            b.get_x() + b.get_width() / 2,
            y,
            label,
            ha="center",
            color="#263B33",
            fontsize=8,
        )

    # Chart 2: Nodes Expanded
    expands = [r.nodes_expanded for r in results]
    ax2 = axes[1]
    ax2.set_facecolor("#F7F9F6")
    bars2 = ax2.bar(algos, expands, color=c_list)
    ax2.set_title("Nodes Expanded (Exploration)", color="#263B33", fontsize=10, fontweight="bold")
    ax2.tick_params(colors="#52665B")
    for b, e in zip(bars2, expands):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.1, f"{e}", ha="center", color="#263B33", fontsize=8)

    # Chart 3: Runtime ms
    times = [r.execution_time_ms for r in results]
    ax3 = axes[2]
    ax3.set_facecolor("#F7F9F6")
    bars3 = ax3.bar(algos, times, color=c_list)
    ax3.set_title("Execution Time (ms)", color="#263B33", fontsize=10, fontweight="bold")
    ax3.tick_params(colors="#52665B")
    for b, t in zip(bars3, times):
        ax3.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.005, f"{t:.3f}", ha="center", color="#263B33", fontsize=8)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#4A5568")
        ax.spines["bottom"].set_color("#4A5568")

    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
