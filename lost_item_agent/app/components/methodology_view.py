"""
app/components/methodology_view.py
----------------------------------
Academic documentation, PEAS formulation, algorithmic theory,
and college evaluation defense guide.
"""

from __future__ import annotations

import streamlit as st


def render_methodology_page():
    """
    Renders comprehensive academic AI theory, PEAS model, and viva presentation guide.
    """
    st.header("📘 AI Search Theory, Problem Formulation & Evaluation Guide")
    st.markdown(
        "This section documents the formal AI problem formulation, mathematical models, "
        "algorithmic guarantees, and presentation guide for college coursework evaluation."
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🤖 PEAS Model",
        "🗺️ State-Space Formulation",
        "⚡ Algorithms & Heuristics",
        "🎯 Multi-Candidate Ranking",
        "🎓 Viva & Demo Guide",
        "📑 Proposal Coverage",
    ])

    # TAB 1: PEAS Model
    with tab1:
        st.subheader("1. PEAS Agent Formulation")
        st.markdown(
            "Under the standard Russell & Norvig artificial intelligence framework, "
            "an intelligent agent is defined by its **PEAS** descriptor:"
        )

        peas_data = {
            "Dimension": [
                "Performance Measure (P)",
                "Environment (E)",
                "Actuators (A)",
                "Sensors (S)",
            ],
            "Formal Definition in This Project": [
                "1. Minimize total movement path cost g(n) (walking distance/time).\n"
                "2. Minimize physical search effort s(n) expended at rooms.\n"
                "3. Maximize probability of early item recovery.\n"
                "4. Minimize computational overhead: nodes expanded, nodes generated, and runtime (ms).",

                "1. Topological Campus: 2 floors, 20 named locations and 26 weighted edges.\n"
                "2. 2D Grid Maps: Configurable dimensions (5×5 to 50×50), random obstacle densities (0%–40%).\n"
                "3. Properties: Discrete, Deterministic, Static/Dynamic (edges can be blocked dynamically), Partially Observable.",

                "1. Navigation commands: move along connected edges or adjacent cardinal grid cells.\n"
                "2. Room search actuator: inspect location for misplaced item.\n"
                "3. Re-planning: each candidate leg is searched from the agent's current simulated location; "
                "changing blocked passages and rerunning recalculates routes.",

                "1. Start location and blocked passages are selected as simulation inputs.\n"
                "2. The designated actual item location is simulation truth used to stop the mission.\n"
                "3. No real location, obstacle, or item sensors are integrated.",
            ],
        }
        import pandas as pd
        st.table(pd.DataFrame(peas_data))

    # TAB 2: State-Space Formulation
    with tab2:
        st.subheader("2. Formal State-Space Problem Formulation")
        st.markdown("""
        Every classical AI search problem is formally defined by a 5-tuple:
        $$\\mathcal{P} = \\langle S, s_0, A(s), \\text{Result}(s, a), \\text{GoalTest}(s), c(s, a, s') \\rangle$$
        """)

        st.markdown("""
        - **State Space ($S$):**
          * *Campus Graph:* The set of 20 distinct campus locations $S = \\{ \\text{Main Entrance, Reception, Library, \\dots, Washroom-F} \\}$.
          * *Grid Map:* The set of free 2D integer coordinates $S = \\{ (r, c) \\mid 0 \\le r < R, 0 \\le c < C, \\text{not Obstacle}(r, c) \\}$.
        - **Initial State ($s_0$):**
          * The student's current position or last known location (e.g. `Main Entrance`).
        - **Actions ($A(s)$):**
          * Available transitions to unblocked adjacent rooms: $A(s) = \\{ v \\in S \\mid (s, v) \\in E \\text{ and } (s, v) \\notin \\text{Blocked} \\}$.
          * On a grid: Cardinal 4-directional steps $\\{ \\text{North, South, East, West} \\}$.
        - **Transition Model ($\text{Result}(s, a)$):**
          * Deterministic: executing action to move to neighbor $v$ places the agent exactly at state $v$.
        - **Goal Test ($\text{GoalTest}(s)$):**
          * $\\text{GoalTest}(s) = \\text{True} \\iff s = s_{\\text{target}}$, where $s_{\\text{target}}$ is a candidate location holding the lost item.
        - **Step Cost ($c(s, a, s')$):**
          * Edge weight $w(s, s') > 0$, representing walking time in minutes or physical distance.
          * Path cost is additive: $g(n) = \\sum_{i=1}^{k} c(s_{i-1}, a_i, s_i)$.
        """)

    # TAB 3: Algorithms & Heuristics
    with tab3:
        st.subheader("3. Algorithm Comparative Analysis & Guarantees")

        st.markdown("""
        | Property | Breadth-First Search (BFS) | Greedy Best-First Search | A* Search |
        |---|---|---|---|
        | **Frontier Data Structure** | FIFO Queue (`collections.deque`) | Priority Queue (`heapq`) | Priority Queue (`heapq`) |
        | **Evaluation Function $f(n)$** | $f(n) = \\text{depth}(n)$ | $f(n) = h(n)$ | $f(n) = g(n) + h(n)$ |
        | **Cost-Optimality** | ❌ Hop-optimal only (suboptimal if edges weighted) | ❌ Not guaranteed | ✅ Provably cost-optimal (with admissible $h$) |
        | **Completeness** | ✅ Complete on finite graphs | ✅ Complete on finite graphs with visited set | ✅ Complete on finite graphs |
        | **Time Complexity** | $O(b^d)$ | $O(b^m)$ worst case | Exponential worst case |
        | **Space Complexity** | $O(b^d)$ (keeps all nodes in memory) | $O(b^m)$ (keeps all frontier nodes) | $O(b^d)$ (keeps all open/closed nodes) |
        """)

        st.markdown("#### 📐 Heuristics and Admissibility Proofs")
        st.markdown("""
        A heuristic $h(n)$ is **admissible** if it never overestimates the true cost to reach the goal:
        $$0 \\le h(n) \\le h^*(n) \\quad \\forall n \\in S$$

        1. **Euclidean Distance on Campus Graph:**
           $$h_{\\text{Euclidean}}(u, v) = \\sqrt{(x_u - x_v)^2 + (y_u - y_v)^2}$$
           *Proof:* For the bundled campus graph, the stored edge weights are at least the Euclidean distance between their endpoint coordinates. The tests verify the resulting heuristic against shortest path costs on that graph. This guarantee is specific to the bundled map and weights.
        2. **Manhattan Distance on 4-Way Grids:**
           $$h_{\\text{Manhattan}}(u, v) = |r_u - r_v| + |c_u - c_v|$$
           *Proof:* In a 4-connected grid without diagonal movement, the minimum number of steps between two cells is their Manhattan displacement. Adding obstacles can only increase the true path cost. Hence $h(n) \\le h^*(n)$ always holds.
        3. **Consistency (Monotonicity):**
           $$h(n) \\le c(n, a, n') + h(n')$$
           The bundled heuristics are consistent on their matching default maps. A* can reopen a node
           when a better path is found, which also supports admissible but inconsistent heuristics.
        """)

    # TAB 4: Multi-Candidate Ranking
    with tab4:
        st.subheader("4. Multi-Candidate Planning Formula")
        st.markdown("""
        In real campus scenarios, a student does not know which room holds their lost item, but has candidate possibilities with prior beliefs.

        #### Mathematical Priority Formula:
        $$\\text{Priority Score}(c) = \\Big( g(s_0 \\to c) + s(c) \\Big) \\times \\Big( 1 - P(\\text{Item at } c) \\Big)$$

        Where:
        - $g(s_0 \\to c)$: Pathfinding cost computed by the search algorithm (walking distance).
        - $s(c)$: Physical search effort required at the room (e.g. 4.0 for a large multi-story Library, 1.0 for a small washroom).
        - $P(\\text{Item at } c) \\in [0, 1]$: Prior probability belief.
        - $(1 - P)$: Cost multiplier — high probability locations get their score reduced, ranking them higher!

        #### ⚠️ Academic Disclosures:
        1. **No Artificial Learning Claims:** The probabilities $P(\\text{Item at } c)$ are student-specified heuristic beliefs (priors), **not** machine-learned from historical training data.
        2. **Greedy Nearest-Neighbor Tour:** The full multi-room visit sequence uses an $O(n^2)$ greedy nearest-neighbor tour. Solving the multi-room sequence optimally is an instance of the Travelling Salesman Problem (TSP), which is NP-hard.
        """)

    # TAB 5: College Evaluation Guide
    with tab5:
        st.subheader("🎓 College Evaluation & Defense Guide")
        st.markdown("Use these model answers when presenting to your project examiner:")

        with st.expander("Q1: Why did you choose A* over Dijkstra?"):
            st.markdown(
                "**Answer:** A* adds a heuristic estimate $h(n)$ to the known path cost $g(n)$. "
                "With an admissible heuristic it preserves optimal path cost; it may expand fewer nodes "
                "than Dijkstra, but that is not guaranteed for every map. Setting $h(n)=0$ makes A* "
                "equivalent to Dijkstra's algorithm."
            )

        with st.expander("Q2: Can you prove Greedy Best-First Search is not optimal?"):
            st.markdown(
                "**Answer:** Yes. In our comparison tab and automated tests, we demonstrate instances where Greedy chooses "
                "a path with an immediate low $h(n)$ that leads into a detour or dead-end, resulting in a higher total path cost "
                "than A*. Greedy minimizes estimated remaining cost $h(n)$ greedily and completely ignores past path cost $g(n)$."
            )

        with st.expander("Q3: Does BFS always find the shortest path?"):
            st.markdown(
                "**Answer:** BFS guarantees the shortest path in terms of **hop count (edge transitions)**, which is optimal "
                "only when all edge weights are equal (uniform cost). On a weighted graph (such as our campus map with corridors of "
                "different lengths), BFS can return a path with higher total walking cost than A*."
            )

        with st.expander("Q4: How do you handle dynamic obstacles (e.g. locked doors)?"):
            st.markdown(
                "**Answer:** The environment supports edge blocking, and blocked edges are excluded from traversable neighbors. "
                "The user selects closures before running a search; running the planner again recomputes routes. "
                "There is no live sensor-based closure detection."
            )

        with st.expander("Q5: What makes your benchmarking scientifically fair?"):
            st.markdown(
                "**Answer:** We enforce 5 strict fairness rules in `BenchmarkRunner`: "
                "1) All algorithms execute on the exact same graph/grid instance per trial; "
                "2) Start and goal pairs are seeded and identical; "
                "3) Search-function wall time is measured (including validation and path reconstruction, excluding UI rendering); "
                "4) Unreachable trials are handled cleanly without crashing; "
                "5) All results are computed live without hard-coded numbers."
            )

    with tab6:
        st.subheader("How the prototype matches the submitted proposal")
        st.caption(
            "This checklist compares the running application with "
            "Lost_Item_Recovery_Agent_Project_Proposal.pdf."
        )
        coverage = pd.DataFrame([
            {
                "Proposal requirement": "PEAS and graph/grid state-space model",
                "Status": "Implemented",
                "Evidence / limitation": "Campus graph, obstacle grid, and formal PEAS/state-space explanation.",
            },
            {
                "Proposal requirement": "Proposal workflow inputs",
                "Status": "Implemented",
                "Evidence / limitation": "Item, last-seen location, current position, visited places, and candidate locations.",
            },
            {
                "Proposal requirement": "Proposal algorithms and heuristic search",
                "Status": "Implemented",
                "Evidence / limitation": "BFS, Greedy, and A* are available with path metrics and heuristic choices.",
            },
            {
                "Proposal requirement": "Proposal recommended order and route visualization",
                "Status": "Implemented",
                "Evidence / limitation": "Candidate ranking, nearest-neighbor visit order, simulated inspections, and campus map.",
            },
            {
                "Proposal requirement": "Proposal benchmark sizes, obstacles, and result metrics",
                "Status": "Mostly implemented",
                "Evidence / limitation": "Seeded size/density scenarios and CSV charts; candidate-count sweeps and memory usage are not benchmarked.",
            },
            {
                "Proposal requirement": "Proposal failure-case evaluation",
                "Status": "Partly implemented",
                "Evidence / limitation": "Unreachable paths and blocked corridors are tested; incorrect last-seen assumptions are not a dedicated benchmark.",
            },
            {
                "Proposal requirement": "Real campus sensors or live closure detection",
                "Status": "Simulation only",
                "Evidence / limitation": "Locations, item truth, and closures are manually selected; no live sensor integration is claimed.",
            },
            {
                "Proposal requirement": "Final report and GitHub repository deliverables",
                "Status": "Outside this prototype",
                "Evidence / limitation": "These are course-submission tasks, not features of the running Streamlit app.",
            },
        ])
        st.dataframe(coverage, use_container_width=True, hide_index=True)
        st.info(
            "The proposal is substantially represented by the prototype. "
            "For an honest submission, document the unimplemented memory metric, "
            "candidate-count benchmark sweep, and final report/repository separately."
        )
