"""
search/astar.py
---------------
A* Search.

Properties
~~~~~~~~~~
* **Complete**: yes, on finite graphs.
* **Optimal**: yes, when the heuristic h(n) is *admissible*
  (never overestimates the true cost to reach the goal).
* **Priority function**: f(n) = g(n) + h(n)
    - g(n) = exact cost from start to node n (path cost so far)
    - h(n) = estimated cost from n to goal (heuristic)
    - f(n) = estimated total cost of a path through n
* **Data structure**: ``heapq`` min-heap keyed by f(n).
* **Node re-opening**: when a node is popped from the heap with a g-value
  higher than the best known g-value, it is skipped (lazy deletion).
  This is correct and efficient for consistent heuristics, and correct
  (though potentially slower) for admissible-only heuristics.

Comparison with Greedy BFS
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Greedy uses h(n) only — ignores how far we have already traveled.
A* uses g(n) + h(n) — balances actual cost with estimated remaining cost.
Result: A* is optimal; Greedy is fast but not optimal.

Comparison with BFS
~~~~~~~~~~~~~~~~~~~
BFS (unweighted) expands nodes in hop-count order.
A* expands nodes in estimated total-cost order.
On unweighted graphs, A* with null heuristic degrades to Dijkstra/BFS.
"""

from __future__ import annotations

import heapq
import time
from typing import Callable, Union

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.models import SearchResult
from search.bfs import _get_neighbors, _validate_node
from search.greedy import _heuristic_name


def astar(
    graph: Union[CampusGraph, GridMap],
    start: str,
    goal: str,
    heuristic: Callable[[str, str, Union[CampusGraph, GridMap]], float],
) -> SearchResult:
    """
    Run A* Search from *start* to *goal*.

    Parameters
    ----------
    graph : CampusGraph | GridMap
        The environment to search.
    start : str
        Name of the starting node / cell.
    goal : str
        Name of the goal node / cell.
    heuristic : callable
        ``h(node_name, goal_name, graph) -> float``
        Must be admissible for optimality guarantee.

    Returns
    -------
    SearchResult
        algorithm = "A*"
        path is optimal when h is admissible.
        path_cost is the minimum weighted path cost.

    Implementation notes
    --------------------
    * g_best[n] tracks the lowest g-value discovered for each node.
    * When a node is popped with g > g_best[n], it is a stale duplicate
      entry and is skipped (lazy deletion pattern).
    * nodes_expanded counts non-stale expansions; reopened nodes count again.
    * nodes_generated counts every push to the frontier.
    """
    t_start = time.perf_counter()

    # ---- validate inputs ----------------------------------------------------
    try:
        _validate_node(graph, start)
        _validate_node(graph, goal)
    except KeyError as exc:
        elapsed = (time.perf_counter() - t_start) * 1000
        return SearchResult(
            algorithm="A*",
            start=start,
            goal=goal,
            success=False,
            execution_time_ms=elapsed,
            heuristic_used=_heuristic_name(heuristic),
            notes=str(exc),
        )

    # ---- trivial case -------------------------------------------------------
    if start == goal:
        elapsed = (time.perf_counter() - t_start) * 1000
        return SearchResult(
            algorithm="A*",
            start=start,
            goal=goal,
            path=[start],
            path_cost=0.0,
            nodes_expanded=1,
            nodes_generated=1,
            execution_time_ms=elapsed,
            success=True,
            heuristic_used=_heuristic_name(heuristic),
        )

    # ---- A* -----------------------------------------------------------------
    # Heap entry: (f_value, tie_break_counter, g_value, node_name)
    # We store only the node name in the heap and reconstruct the path via
    # a came_from dict — avoids copying growing path lists on every push.
    counter = 0
    g_start = 0.0
    h_start = heuristic(start, goal, graph)
    f_start = g_start + h_start

    heap: list[tuple[float, int, float, str]] = [(f_start, counter, g_start, start)]

    # Best g-value seen for each node
    g_best: dict[str, float] = {start: 0.0}

    # Predecessor map for path reconstruction
    came_from: dict[str, str | None] = {start: None}

    nodes_expanded = 0
    nodes_generated = 1  # start node

    while heap:
        f_val, _, g_val, current = heapq.heappop(heap)

        # Skip stale entry (a better path to this node was already found)
        if g_val > g_best.get(current, float("inf")):
            continue

        nodes_expanded += 1

        # ---- goal test (on expansion, not generation) ----------------------
        if current == goal:
            elapsed = (time.perf_counter() - t_start) * 1000
            path = _reconstruct_path(came_from, goal)
            return SearchResult(
                algorithm="A*",
                start=start,
                goal=goal,
                path=path,
                path_cost=g_val,
                nodes_expanded=nodes_expanded,
                nodes_generated=nodes_generated,
                execution_time_ms=elapsed,
                success=True,
                heuristic_used=_heuristic_name(heuristic),
            )

        for neighbor, weight in _get_neighbors(graph, current):
            tentative_g = g_val + weight

            if tentative_g < g_best.get(neighbor, float("inf")):
                # Found a better path to neighbor
                g_best[neighbor] = tentative_g
                came_from[neighbor] = current
                h_n = heuristic(neighbor, goal, graph)
                f_n = tentative_g + h_n
                counter += 1
                nodes_generated += 1
                heapq.heappush(heap, (f_n, counter, tentative_g, neighbor))

    # ---- goal unreachable ---------------------------------------------------
    elapsed = (time.perf_counter() - t_start) * 1000
    return SearchResult(
        algorithm="A*",
        start=start,
        goal=goal,
        success=False,
        nodes_expanded=nodes_expanded,
        nodes_generated=nodes_generated,
        execution_time_ms=elapsed,
        heuristic_used=_heuristic_name(heuristic),
        notes="Goal is unreachable from start.",
    )


# ---------------------------------------------------------------------------
# Path reconstruction
# ---------------------------------------------------------------------------

def _reconstruct_path(came_from: dict[str, str | None], goal: str) -> list[str]:
    """Walk the came_from predecessor map backwards from goal to start."""
    path: list[str] = []
    current: str | None = goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
