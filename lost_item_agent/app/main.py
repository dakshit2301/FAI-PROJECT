"""
app/main.py
-----------
Lost Item Recovery Agent: Streamlit Application Entry Point.
Foundation of AI — Project-Based Learning.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root directory is in sys.path
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

# Streamlit Page Setup
st.set_page_config(
    page_title="Lost Item Recovery Agent",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS layered on the accessible light Streamlit theme.
THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], input, button, textarea,
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    div[data-testid="stWidgetLabel"] p {
        font-family: "DM Sans", "Segoe UI", sans-serif !important;
        font-optical-sizing: auto;
    }
    [data-testid="stHeading"] h1,
    [data-testid="stHeading"] h2,
    [data-testid="stHeading"] h3,
    [data-testid="stHeading"] h4,
    [data-testid="stHeading"] h5,
    [data-testid="stHeading"] h6 {
        font-family: "Manrope", "DM Sans", sans-serif !important;
        letter-spacing: -0.035em;
    }
    code, pre, [data-testid="stMetricValue"] {
        font-family: "DM Mono", "Cascadia Code", monospace;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 7% 0%, rgba(22, 120, 111, 0.075), transparent 30%),
            #F4F7F3;
        color: #203331;
    }
    .block-container {
        max-width: 1420px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }
    [data-testid="stMarkdownContainer"] p {
        color: #465A50;
    }
    section[data-testid="stSidebar"] {
        background: #EDF2EC;
        border-right: 1px solid #DCE6DE;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: #17453E;
        letter-spacing: -0.045em;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 10px;
    }
    .hero-container {
        position: relative;
        overflow: hidden;
        padding: 36px 40px;
        background:
            radial-gradient(ellipse at 88% 0%, rgba(148, 210, 173, 0.18), transparent 34%),
            linear-gradient(115deg, #173D38 0%, #1B5148 63%, #23665A 100%);
        border: 1px solid #286458;
        border-radius: 22px;
        margin: 0 0 30px;
        box-shadow: 0 18px 40px rgba(31, 76, 66, 0.13);
    }
    .hero-title {
        max-width: 780px;
        font-family: "Manrope", "DM Sans", sans-serif;
        font-size: clamp(34px, 4.4vw, 54px);
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.08;
        letter-spacing: -0.055em;
        margin: 8px 0 12px;
    }
    .hero-subtitle {
        max-width: 700px;
        font-size: 16px;
        line-height: 1.65;
        color: #D8E9E2;
        margin: 0 0 20px;
    }
    .hero-kicker {
        color: #A6E3C5;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.8px;
        text-transform: uppercase;
    }
    .badge {
        display: inline-block;
        padding: 7px 12px;
        font-size: 11px;
        font-weight: 700;
        border-radius: 999px;
        margin: 0 7px 5px 0;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        color: #F0F8F4;
    }
    .badge-bfs { border-color: rgba(132, 186, 244, 0.38); }
    .badge-greedy { border-color: rgba(246, 191, 123, 0.38); }
    .badge-astar { border-color: rgba(142, 221, 182, 0.42); }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #DEE7E0;
        border-radius: 17px;
        box-shadow: 0 5px 18px rgba(37, 68, 52, 0.035);
    }
    div[data-testid="stMetric"] {
        background: #F8FAF7;
        border: 1px solid #E3EAE4;
        border-radius: 13px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] {
        color: #64766C;
        font-size: 12px;
        font-weight: 650;
    }
    div[data-testid="stMetricValue"] {
        color: #17453E;
        letter-spacing: -0.04em;
    }
    div[data-testid="stButton"] button {
        border-radius: 11px;
        font-weight: 700;
        min-height: 46px;
        transition: transform 120ms ease, box-shadow 120ms ease;
    }
    button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(100deg, #176B62, #178578);
        border: 1px solid #16786F;
        color: #FFFFFF;
        box-shadow: 0 7px 15px rgba(22, 120, 111, 0.16);
    }
    button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(100deg, #125A52, #146E64);
        border-color: #125A52;
        box-shadow: 0 9px 19px rgba(22, 120, 111, 0.23);
    }
    button[data-testid="stBaseButton-secondary"] {
        background: #FFFFFF;
        border-color: #D6E1D9;
        color: #29473F;
    }
    [data-tag] {
        background-color: #E4F1E8 !important;
        color: #1C5A49 !important;
        border: 1px solid #C5DEC9;
        border-radius: 7px !important;
    }
    div[data-testid="stSelectbox"] > label,
    div[data-testid="stMultiSelect"] > label,
    div[data-testid="stSlider"] > label {
        color: #344B43;
        font-weight: 650;
    }
    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid #DEE7E0;
        border-radius: 13px;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #DEE7E0;
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stAlert"] {
        border-radius: 12px;
    }
    [data-testid="stMarkdownContainer"] a {
        color: #16786F;
        text-underline-offset: 3px;
    }
    [data-testid="stCaptionContainer"] {
        color: #53665C;
    }
    @media (max-width: 700px) {
        .block-container { padding: 1.2rem 1rem 2.5rem; }
        .hero-container { padding: 25px 22px; border-radius: 17px; }
        .hero-title { font-size: 34px; }
    }
</style>
"""


def main():
    st.html(THEME_CSS)

    # Compact project identity and algorithm key.
    st.markdown("""
    <div class="hero-container">
        <div class="hero-kicker">Foundation of AI · Interactive Project</div>
        <div class="hero-title">Find your lost item.</div>
        <div class="hero-subtitle">
            A campus search simulation that ranks likely places, plans routes, and compares classical AI search algorithms.
        </div>
        <div>
            <span class="badge badge-bfs">BFS · fewest hops</span>
            <span class="badge badge-greedy">Greedy · goal directed</span>
            <span class="badge badge-astar">A* · cost + heuristic</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar Navigation
    st.sidebar.markdown("## 🧭 Campus Search")
    st.sidebar.caption("LOST ITEM RECOVERY AGENT")
    nav_mode = st.sidebar.radio(
        "Explore",
        options=[
            "🧭 Agent Workspace & Campus Map",
            "🏁 2D Grid Search Playground",
            "⚖️ Multi-Algorithm Comparison",
            "📊 Experimental Benchmarks",
            "📘 AI Theory & Methodology",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏛️ Environment Topology")
    st.sidebar.info(
        "**Campus** · 20 locations · 2 floors · 26 corridors\n\n"
        "**Grid** · 5×5 to 50×50 · up to 40% obstacles"
    )

    st.sidebar.markdown("### 🎓 Academic Information")
    st.sidebar.caption(
        "**Course:** Foundation of AI (Semester 5)\n\n"
        "**Project:** Project-Based Learning (PBL)\n\n"
        "**Algorithms:** BFS, Greedy Best-First, A*\n\n"
        "**Mode:** Interactive search simulation"
    )

    # Route based on navigation selection
    if nav_mode == "🧭 Agent Workspace & Campus Map":
        render_search_workspace()

    elif nav_mode == "🏁 2D Grid Search Playground":
        render_grid_search_playground()

    elif nav_mode == "⚖️ Multi-Algorithm Comparison":
        st.subheader("⚖️ Side-by-Side Algorithm Comparison")
        st.markdown(
            "Execute **BFS**, **Greedy Best-First**, and **A*** simultaneously on the identical campus "
            "topology or grid to evaluate trade-offs in optimality, exploration, and runtime."
        )

        all_locs = location_names()
        c1, c2 = st.columns(2)
        with c1:
            comp_start = st.selectbox("Start Location", options=all_locs, index=all_locs.index("Main Entrance"))
        with c2:
            comp_goal = st.selectbox("Target Goal Location", options=all_locs, index=all_locs.index("Classroom-102"))

        campus = build_default_campus()
        render_algorithm_comparison(campus, start=comp_start, goal=comp_goal, is_grid=False)

    elif nav_mode == "📊 Experimental Benchmarks":
        render_benchmark_page()

    elif nav_mode == "📘 AI Theory & Methodology":
        render_methodology_page()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #718096; font-size: 12px;'>"
        "Lost Item Recovery Agent • Foundation of AI Course Project"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
