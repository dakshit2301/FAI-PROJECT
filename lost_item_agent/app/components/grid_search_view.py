"""
app/components/grid_search_view.py
----------------------------------
Interactive 2D Grid Search Playground for testing algorithms on configurable grids
with random obstacles, start/goal placement, and route visualization.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from app.components.campus_map_view import draw_grid_map
from app.components.metrics_card import render_search_result_metrics
from environment.grid import GridMap
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import manhattan_distance


def render_grid_search_playground():
    """
    Interactive 2D grid search view.
    """
    st.subheader("🏁 2D Grid Search Playground")
    st.markdown(
        "Generate configurable 2D grids with randomized obstacles, select start and goal coordinates, "
        "and observe how BFS, Greedy, and A* navigate obstacles."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rows = st.slider("Rows", 5, 30, 15)
    with col2:
        cols = st.slider("Columns", 5, 30, 15)
    with col3:
        density = st.slider("Obstacle Density", 0.0, 0.40, 0.20, step=0.05)
    with col4:
        seed = st.number_input("Seed", value=42, min_value=1, max_value=99999)

    # Build grid
    grid = GridMap.from_obstacle_density(rows=rows, cols=cols, density=density, seed=seed)

    # Coordinate selectors
    free_cells = [grid.to_node_name(r, c) for r, c in grid.all_cells() if not grid.is_obstacle(r, c)]
    if len(free_cells) < 2:
        st.error("Too many obstacles! Not enough free cells to search.")
        return

    col_s, col_g, col_a = st.columns(3)
    with col_s:
        start_cell = st.selectbox("Start Cell (r,c)", options=free_cells, index=0)
    with col_g:
        goal_cell = st.selectbox("Goal Cell (r,c)", options=free_cells, index=len(free_cells) - 1)
    with col_a:
        algo_choice = st.selectbox("Algorithm", options=["A* (Manhattan)", "BFS (Breadth-First)", "Greedy Best-First"])

    # Run search
    if algo_choice.startswith("A*"):
        res = astar(grid, start_cell, goal_cell, manhattan_distance)
    elif algo_choice.startswith("BFS"):
        res = bfs(grid, start_cell, goal_cell)
    else:
        res = greedy_best_first(grid, start_cell, goal_cell, manhattan_distance)

    render_search_result_metrics(res, title=f"Grid Search Result: {res.algorithm}")

    # Map visualization
    fig = draw_grid_map(
        grid=grid,
        start_pos=start_cell,
        path=res.path if res.success else None,
        recovered_pos=goal_cell if res.success else None,
    )
    st.pyplot(fig)
    plt.close(fig)
