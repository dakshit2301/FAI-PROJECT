"""
app/main.py
-----------
Lost Item Recovery Agent: Streamlit application entry point.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.components.algorithm_comparison_view import render_algorithm_comparison
from app.components.benchmark_view import render_benchmark_page
from app.components.grid_search_view import render_grid_search_playground
from app.components.methodology_view import render_methodology_page
from app.components.search_workspace import render_search_workspace
from environment.locations import build_default_campus, location_names

st.set_page_config(
    page_title="Lost Item Recovery Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)

THEME_CSS = """
<style>
    :root {
        --ink: #18222d;
        --muted: #62707f;
        --paper: #f7f8f5;
        --panel: #ffffff;
        --line: #dce2dd;
        --navy: #173f5f;
        --teal: #176b62;
        --warm: #c77732;
    }
    html, body, [data-testid="stAppViewContainer"], input, button, textarea {
        font-family: "Aptos", "Segoe UI", Arial, sans-serif;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container {
        max-width: 1280px; padding-top: 2.1rem; padding-bottom: 3.25rem;
    }
    section[data-testid="stSidebar"] {
        background: #eef2ef; border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
    section[data-testid="stSidebar"] label { color: #586775; font-size: .78rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        color: var(--ink); font-size: .95rem; font-weight: 600; letter-spacing: 0; text-transform: none;
    }
    h1 { color: var(--navy); font-size: 2.15rem !important; letter-spacing: -.04em; margin-bottom: .05rem !important; }
    h2, h3 { color: var(--navy); letter-spacing: -.02em; }
    [data-testid="stCaptionContainer"] { color: var(--muted); }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--panel); border: 1px solid var(--line); border-radius: 10px; box-shadow: none;
    }
    div[data-testid="stMetric"] {
        background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: .8rem .9rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: .78rem; }
    [data-testid="stMetricValue"] { color: var(--navy); font-weight: 700; }
    div[data-testid="stButton"] button {
        border-radius: 7px; font-weight: 650; min-height: 42px;
    }
    button[data-testid="stBaseButton-primary"] {
        background: var(--teal); border-color: var(--teal); color: #fff;
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    [data-testid="stTabs"] [role="tablist"] { gap: 1.25rem; border-bottom: 1px solid var(--line); }
    [data-testid="stTabs"] [role="tab"] { color: var(--muted); font-weight: 600; padding: .65rem .1rem; }
    [data-testid="stTabs"] [aria-selected="true"] { color: var(--navy); border-bottom-color: var(--teal); }
    .project-kicker { color: var(--teal); font-size: .76rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .35rem; }
    .sidebar-brand { color: var(--navy); font-size: 1.18rem; font-weight: 750; line-height: 1.2; margin-bottom: .25rem; }
    .sidebar-note { color: var(--muted); font-size: .84rem; line-height: 1.45; margin-bottom: 1.4rem; }
    div[data-testid="stAlert"] { border-radius: 8px; }
    @media (max-width: 700px) { .block-container { padding-top: 1.25rem; } h1 { font-size: 1.75rem !important; } }
</style>
"""

NAV_PAGES = [
    "Search Workspace",
    "Grid Search",
    "Algorithm Comparison",
    "Benchmarks",
    "Methodology",
]


def main() -> None:
    st.html(THEME_CSS)
    st.sidebar.markdown('<div class="sidebar-brand">Lost Item<br>Recovery Agent</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="sidebar-note">Foundation of AI<br>Campus search simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="project-kicker">Foundation of AI · Applied Agent Project</div>', unsafe_allow_html=True)
    st.title("Lost Item Recovery Agent")
    st.caption("Compare transparent search strategies on a simulated campus graph and obstacle grid.")

    page = st.sidebar.radio("Project sections", options=NAV_PAGES, index=0)

    if page == "Search Workspace":
        render_search_workspace()
    elif page == "Grid Search":
        render_grid_search_playground()
    elif page == "Algorithm Comparison":
        st.subheader("Algorithm comparison")
        st.write(
            "Run BFS, Greedy Best-First Search, and A* on the same campus route "
            "to compare path cost, exploration, and runtime."
        )
        all_locs = location_names()
        col_start, col_goal = st.columns(2)
        with col_start:
            start = st.selectbox(
                "Start location",
                options=all_locs,
                index=all_locs.index("Main Entrance"),
            )
        with col_goal:
            goal = st.selectbox(
                "Goal location",
                options=all_locs,
                index=all_locs.index("Classroom-102"),
            )
        render_algorithm_comparison(
            build_default_campus(),
            start=start,
            goal=goal,
            is_grid=False,
        )
    elif page == "Benchmarks":
        render_benchmark_page()
    else:
        render_methodology_page()


if __name__ == "__main__":
    main()
