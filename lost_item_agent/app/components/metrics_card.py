"""
app/components/metrics_card.py
------------------------------
Aesthetic academic metrics cards and status badges for Streamlit.
"""

from __future__ import annotations

import streamlit as st
from environment.models import SearchResult
from planner.candidate_planner import CandidateResult


def render_search_result_metrics(result: SearchResult, title: str = "Execution Metrics"):
    """
    Renders a responsive multi-column metric card display for a single SearchResult.
    """
    st.markdown(f"### {title}")

    # Success / Failure banner
    if result.success:
        st.success(
            f"**Candidate reached.** Found a route from `{result.start}` to `{result.goal}` "
            f"using **{result.algorithm}** (Heuristic: `{result.heuristic_used or 'None'}`)."
        )
    else:
        st.error(
            f"**Candidate unreachable.** No valid route exists from `{result.start}` to `{result.goal}` "
            f"(Notes: {result.notes or 'frontier exhausted'})."
        )

    # Split the metrics into two readable rows so labels do not truncate on laptop widths.
    primary_cols = st.columns(3)

    with primary_cols[0]:
        st.metric(
            label="Path Cost",
            value=f"{result.path_cost:.2f}" if result.success else "N/A",
            help="Sum of edge weights along the returned path. Equal to hop count on uniform grids.",
        )

    with primary_cols[1]:
        st.metric(
            label="Path Hops",
            value=f"{result.path_length}" if result.success else "N/A",
            help="Number of transitions (edges) from start to goal.",
        )

    with primary_cols[2]:
        st.metric(
            label="Expanded",
            value=f"{result.nodes_expanded}",
            help="Number of states popped from the priority queue / frontier.",
        )

    secondary_cols = st.columns(2)
    with secondary_cols[0]:
        st.metric(
            label="Generated",
            value=f"{result.nodes_generated}",
            help="Total valid neighbor states added to the frontier (including duplicates).",
        )

    with secondary_cols[1]:
        st.metric(
            label="Execution Time",
            value=f"{result.execution_time_ms:.3f} ms",
            help="Measured by the search function, including validation and path reconstruction.",
        )


def render_candidate_metrics_table(results: list[CandidateResult]):
    """
    Renders a compact ranking table and a separate search-work breakdown.
    """
    if not results:
        st.info("No candidates evaluated.")
        return

    import pandas as pd

    rows = []
    work_rows = []
    for r in results:
        rows.append({
            "Rank": f"#{r.rank}",
            "Candidate Location": r.candidate,
            "Reachable": "Yes" if r.reachable else "No",
            "Walking Cost": f"{r.pathfinding_cost:.1f}" if r.reachable else "∞",
            "Room Search": f"{r.search_cost:.1f}",
            "Belief P(Item)": f"{r.probability_weight:.2f}",
            "Priority Score": f"{r.priority_score:.2f}" if r.reachable else "∞",
        })
        work_rows.append({
            "Candidate": r.candidate,
            "Nodes Expanded": r.algorithm_result.nodes_expanded,
            "Nodes Generated": r.algorithm_result.nodes_generated,
            "Search Time (ms)": f"{r.algorithm_result.execution_time_ms:.3f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    with st.expander("Per-candidate search work"):
        st.dataframe(
            pd.DataFrame(work_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "**Formula**: `Priority Score = (Pathfinding Cost + Search Effort) × (1 - Belief Probability)`. "
        "Lower score indicates higher investigation priority. "
        "Academic honesty notice: Belief probabilities are student-specified priors, not machine-learned."
    )
