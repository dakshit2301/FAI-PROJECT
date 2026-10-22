"""
search/greedy.py
----------------
Greedy Best-First Search (GBFS).

Properties
~~~~~~~~~~
* **Complete**: NOT guaranteed on graphs with cycles (may revisit nodes
  indefinitely without a visited set).  With a visited set (as implemented
  here) it is complete on finite graphs.
* **Optimal**: NOT guaranteed.  GBFS can return a longer/costlier path than
  the true optimum because it ignores g(n) (the cost already incurred).
* **Heuristic**: uses h(n) only — the estimated cost to goal.
* **Data structure**: ``heapq`` min-heap keyed by h(n).
* **Speed**: typically expands fewer nodes than BFS on open maps, but can
  be fooled by misleading heuristics on maps with obstacles.

Academic note
~~~~~~~~~~~~~
Do not claim Greedy always finds the shortest path.  In the presence of
obstacles, it often takes a longer detour than A*.  This is demonstrated
empirically in the benchmark section.
"""

from __future__ import annotations

import heapq
import time
from typing import Callable, Union

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.models import SearchResult
from search.bfs import _get_neighbors, _validate_node


def greedy_best_first(
    graph: Union[CampusGraph, GridMap],
    start: str,
    goal: str,
    heuristic: Callable[[str, str, Union[CampusGraph, GridMap]], float],
) -> SearchResult:
    """
    Run Greedy Best-First Search from *start* to *goal*.

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
        Must return a non-negative value; admissibility not required.

    Returns
    -------
    SearchResult
        algorithm = "Greedy"
        heuristic_used = name inferred from function name.
        path may be suboptimal.
    """
    t_start = time.perf_counter()

    # ---- validate inputs ----------------------------------------------------
    try:
        _validate_node(graph, start)
        _validate_node(graph, goal)
    except KeyError as exc:
        elapsed = (time.perf_counter() - t_start) * 1000
        return SearchResult(
            algorithm="Greedy",
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
            algorithm="Greedy",
            start=start,
            goal=goal,
            path=[start],
            path_cost=0.0,
            nodes_expanded=1,
            nodes_generated=1,
            execution_time_ms=elapsed,
            success=True,
            heuristic_used=_heuristic_name(heuristic),
            explored_nodes=[start],
        )

    # ---- Greedy BFS ---------------------------------------------------------
    # Heap entry: (h_value, tie_break_counter, node_name, path_so_far, cost_so_far)
    # tie_break_counter prevents comparison of list[str] when h values are equal.
    counter = 0
    h_start = heuristic(start, goal, graph)
    heap: list[tuple[float, int, str, list[str], float]] = [
        (h_start, counter, start, [start], 0.0)
    ]

    visited: set[str] = set()
    nodes_expanded = 0
    nodes_generated = 1  # start
    explored_nodes: list[str] = []

    while heap:
        _, _, current, path, cost = heapq.heappop(heap)

        if current in visited:
            continue
        visited.add(current)
        nodes_expanded += 1
        explored_nodes.append(current)

        if current == goal:
            elapsed = (time.perf_counter() - t_start) * 1000
            return SearchResult(
                algorithm="Greedy",
                start=start,
                goal=goal,
                path=path,
                path_cost=cost,
                nodes_expanded=nodes_expanded,
                nodes_generated=nodes_generated,
                execution_time_ms=elapsed,
                success=True,
                heuristic_used=_heuristic_name(heuristic),
                explored_nodes=explored_nodes,
            )

        for neighbor, weight in _get_neighbors(graph, current):
            if neighbor not in visited:
                h_n = heuristic(neighbor, goal, graph)
                counter += 1
                nodes_generated += 1
                heapq.heappush(
                    heap,
                    (h_n, counter, neighbor, path + [neighbor], cost + weight),
                )

    # ---- goal unreachable ---------------------------------------------------
    elapsed = (time.perf_counter() - t_start) * 1000
    return SearchResult(
        algorithm="Greedy",
        start=start,
        goal=goal,
        success=False,
        nodes_expanded=nodes_expanded,
        nodes_generated=nodes_generated,
        execution_time_ms=elapsed,
        heuristic_used=_heuristic_name(heuristic),
        notes="Goal is unreachable from start.",
        explored_nodes=explored_nodes,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _heuristic_name(h: Callable) -> str:
    """Extract a human-readable name from a heuristic function."""
    return getattr(h, "__name__", str(h))
