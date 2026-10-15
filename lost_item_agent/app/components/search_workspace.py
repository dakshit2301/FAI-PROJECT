"""
app/components/search_workspace.py
----------------------------------
Interactive search workspace for configuring lost items, candidate locations,
dynamic obstacles, and executing intelligent search missions.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from app.components.campus_map_view import draw_campus_map
from app.components.metrics_card import (
    render_candidate_metrics_table,
    render_search_result_metrics,
)
from environment.graph import CampusGraph
from environment.locations import (
    ITEM_TYPE_CANDIDATES,
    build_default_campus,
    location_names,
)
from planner.candidate_planner import CandidatePlanner
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import (
    euclidean_distance,
    manhattan_distance,
    null_heuristic,
)


def get_fresh_campus(blocked_edges: list[tuple[str, str]]) -> CampusGraph:
    """Builds a campus graph and applies any active blocked edges."""
    campus = build_default_campus()
    for u, v in blocked_edges:
        if campus.has_edge(u, v):
            campus.block_edge(u, v)
    return campus


def render_search_workspace():
    """
    Renders the campus lost-item planning and recovery workspace.
    """
    st.markdown("## Plan a campus search")
    st.caption(
        "Set the last-seen point and your current position, then let the agent "
        "prioritize candidate rooms and calculate a route."
    )

    all_locs = location_names()
    main_entrance = all_locs.index("Main Entrance") if "Main Entrance" in all_locs else 0

    with st.container(border=True):
        st.markdown("### 01 · Search context")
        col1, col2, col3 = st.columns(3)

        with col1:
            item_categories = list(ITEM_TYPE_CANDIDATES.keys()) + ["other / custom"]
            selected_category = st.selectbox(
                "What did you lose?",
                options=item_categories,
                index=0,
                help="Choose an item category to suggest likely campus locations.",
            )
            item_description = selected_category
            if selected_category == "other / custom":
                item_description = st.text_input(
                    "Describe the item",
                    placeholder="e.g. blue water bottle",
                    key="custom_item_description",
                ) or "custom item"

        with col2:
            last_known_location = st.selectbox(
                "Where did you last see it?",
                options=all_locs,
                index=main_entrance,
                key="last_known_location",
                help="Used as context for the search and shown on the campus map.",
            )

        with col3:
            start_location = st.selectbox(
                "Where are you now?",
                options=all_locs,
                index=main_entrance,
                key="current_location",
                help="The agent starts each route from your current position.",
            )

        candidate_col, visited_col = st.columns(2)
        with candidate_col:
            default_candidates = ITEM_TYPE_CANDIDATES.get(
                selected_category, ["Library", "Lab-A", "Classroom-101"]
            )
            selected_candidates = st.multiselect(
                "Likely places to search",
                options=all_locs,
                default=default_candidates,
                key=f"candidates_{selected_category}",
                help="Select likely rooms; suggested locations depend on the item category.",
            )

        with visited_col:
            visited_locations = st.multiselect(
                "Places visited since you last saw it",
                options=all_locs,
                key="visited_locations",
                help="Visited places are added to the candidate search list and highlighted on the map.",
            )

        search_candidates = list(dict.fromkeys(
            [*selected_candidates, *visited_locations]
        ))

    candidate_probs: dict[str, float] = {}
    with st.expander("Adjust location beliefs", expanded=False):
        st.caption(
            "These are your manual prior beliefs, not learned probabilities. "
            "The model's room-search effort remains fixed for each location."
        )
        if search_candidates:
            prob_cols = st.columns(min(4, len(search_candidates)))
            for i, cand in enumerate(search_candidates):
                with prob_cols[i % len(prob_cols)]:
                    candidate_probs[cand] = st.slider(
                        f"Belief · {cand}",
                        min_value=0.05,
                        max_value=0.95,
                        value=0.50,
                        step=0.05,
                        key=f"prob_{cand}",
                    )
        else:
            st.info("Add at least one likely or visited location.")

    with st.expander("Environment options · simulate blocked corridors"):
        st.markdown(
            "Choose closures before the run. The simulation removes those connections, "
            "then calculates routes using the updated campus graph."
        )
        corridor_options = [
            ("Corridor-G1", "Library"),
            ("Corridor-G2", "Lab-A"),
            ("Corridor-G1", "Stairwell"),
            ("Stairwell", "Corridor-F1"),
            ("Corridor-F1", "Classroom-102"),
            ("Main Entrance", "Corridor-G1"),
        ]
        blocked_labels = [f"{u} ↔ {v}" for u, v in corridor_options]
        chosen_blocked = st.multiselect(
            "Select Passages to Block",
            options=blocked_labels,
            default=[],
            help="Simulates maintenance closures or locked access doors.",
        )
        active_blocked_edges = []
        for label in chosen_blocked:
            u, v = label.split(" ↔ ")
            active_blocked_edges.append((u, v))

    st.markdown("### 02 · Search strategy")
    col_alg1, col_alg2, col_alg3 = st.columns([1.3, 1.3, 1.1])
    with col_alg1:
        algo_choice = st.selectbox(
            "Algorithm",
            options=["A* Search (Optimal & Informed)", "Breadth-First Search (BFS)", "Greedy Best-First Search"],
            index=0,
        )
    with col_alg2:
        heuristic_choice = st.selectbox(
            "Heuristic",
            options=["Euclidean Distance (Straight-line, Admissible)", "Manhattan Distance", "Null Heuristic (Dijkstra baseline)"],
            index=0,
            disabled=("BFS" in algo_choice),
        )
    with col_alg3:
        sim_target = st.selectbox(
            "Actual item location · simulation",
            options=search_candidates if search_candidates else ["None"],
            help="Simulation truth used to stop the mission; it is not a sensor reading.",
        )

    algo_key = "astar" if "A*" in algo_choice else ("bfs" if "BFS" in algo_choice else "greedy")
    heuristic_func = euclidean_distance
    if "Manhattan" in heuristic_choice:
        heuristic_func = manhattan_distance
    elif "Null" in heuristic_choice:
        heuristic_func = null_heuristic

    # The two actions share the same validated search configuration.
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_plan_btn = st.button(
            "Build search plan",
            type="primary",
            use_container_width=True,
        )
    with col_btn2:
        run_sim_btn = st.button(
            "Simulate recovery mission",
            use_container_width=True,
        )

    if run_plan_btn:
        st.session_state["search_mode"] = "plan"
    elif run_sim_btn:
        st.session_state["search_mode"] = "mission"

    search_mode = st.session_state.get("search_mode")
    campus = get_fresh_campus(active_blocked_edges)

    if search_mode:
        if not search_candidates:
            st.warning("Select at least one likely place or visited location.")
            return

        planner = CandidatePlanner(campus, algorithm=algo_key, heuristic=heuristic_func)
        plan_results = planner.plan(start_location, search_candidates, candidate_probs)
        visit_order = planner.recommended_visit_order(plan_results, start=start_location)

        st.markdown("#### Prioritized candidate investigation")
        render_candidate_metrics_table(plan_results)

        st.markdown(
            f"**Recommended Multi-Room Tour (Greedy Nearest-Neighbor):** "
            f"`{' → '.join([start_location] + visit_order)}`"
        )

        recovered_index: int | None = None
        if search_mode == "mission":
            mission_steps = planner.execute_mission(
                start_location,
                visit_order,
                actual_location=sim_target,
            )
            mission_rows = []
            path_nodes = [start_location]
            for step in mission_steps:
                result = step.algorithm_result
                status = (
                    f"{item_description} recovered"
                    if step.item_found
                    else "Not found"
                    if result.success
                    else "Location unreachable"
                )
                mission_rows.append({
                    "From": step.from_location,
                    "Candidate inspected": step.candidate,
                    "Result": status,
                    "Route": " → ".join(result.path) if result.success else "No route",
                    "Path cost": result.path_cost if result.success else None,
                    "Nodes expanded": result.nodes_expanded,
                    "Runtime (ms)": result.execution_time_ms,
                })
                if result.success:
                    path_nodes.extend(result.path[1:])
                if step.item_found:
                    recovered_index = len(path_nodes) - 1

            st.markdown("#### Candidate inspection results")
            if mission_rows:
                st.dataframe(mission_rows, use_container_width=True, hide_index=True)

            if recovered_index is not None:
                st.success(
                    f"**{item_description}** recovered at **{sim_target}** after "
                    f"{len(mission_steps) - 1} unsuccessful candidate inspection(s)."
                )
            elif sim_target not in visit_order:
                st.error(
                    f"The simulated item location **{sim_target}** is unreachable "
                    "with the currently blocked passages."
                )
            else:
                st.warning("The simulated item was not recovered during this mission.")
        else:
            target_goal = plan_results[0].candidate if plan_results else None
            path_nodes = []
            if target_goal:
                if algo_key == "bfs":
                    search_res = bfs(campus, start_location, target_goal)
                elif algo_key == "greedy":
                    search_res = greedy_best_first(
                        campus, start_location, target_goal, heuristic_func
                    )
                else:
                    search_res = astar(
                        campus, start_location, target_goal, heuristic_func
                    )

                render_search_result_metrics(
                    search_res,
                    title=(
                        f"Pathfinding Result: `{start_location}` → "
                        f"`{target_goal}` ({search_res.algorithm})"
                    ),
                )
                path_nodes = search_res.path if search_res.success else []

        st.markdown("#### Campus route")
        step_path = path_nodes
        if search_mode == "mission" and len(path_nodes) > 1:
            step_idx = st.slider(
                "Search Mission Progress (Steps Traversed)",
                min_value=1,
                max_value=len(path_nodes),
                value=len(path_nodes),
            )
            step_path = path_nodes[:step_idx]

        recovered_node = None
        if (
            search_mode == "mission"
            and recovered_index is not None
            and len(step_path) - 1 >= recovered_index
        ):
            recovered_node = sim_target

        fig_map = draw_campus_map(
            graph=campus,
            start_node=start_location,
            last_known_node=last_known_location,
            path=step_path,
            candidate_nodes=search_candidates,
            candidate_probs=candidate_probs,
            recovered_node=recovered_node,
            visited_nodes=visited_locations,
            blocked_edges=active_blocked_edges,
        )
        st.pyplot(fig_map, use_container_width=True)
        plt.close(fig_map)

    else:
        map_col, guide_col = st.columns([1.35, 0.65], vertical_alignment="center")
        with map_col:
            with st.container(border=True):
                st.markdown("### Campus map")
                st.caption(
                    "Teal: current position · violet: last seen · orange: candidate · "
                    "purple outline: visited"
                )
                fig_initial = draw_campus_map(
                    graph=campus,
                    start_node=start_location,
                    last_known_node=last_known_location,
                    candidate_nodes=search_candidates,
                    candidate_probs=candidate_probs,
                    visited_nodes=visited_locations,
                    blocked_edges=active_blocked_edges,
                )
                st.pyplot(fig_initial, use_container_width=True)
                plt.close(fig_initial)
        with guide_col:
            st.markdown("### Your search, in 3 steps")
            st.markdown(
                "1. **Set context** — choose where you last saw the item and where you are now.\n"
                "2. **Choose locations** — combine likely rooms with places you visited.\n"
                "3. **Run the agent** — compare the recommended order or simulate inspections."
            )
            st.info(
                f"Ready to search **{len(search_candidates)}** location(s) "
                f"with **{algo_choice.split(' (')[0]}**."
            )
