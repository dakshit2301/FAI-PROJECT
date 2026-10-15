"""
search/bfs.py
-------------
Breadth-First Search (BFS).

Properties
~~~~~~~~~~
* **Complete**: always finds a solution if one exists (finite graphs).
* **Optimal**: returns the path with the fewest *hops* (edge count).
  On an *unweighted* graph this equals the shortest path.
  On a *weighted* graph, BFS hop-count optimality does NOT imply
  cost optimality — use A* for weighted shortest-path.
* **Time complexity**: O(b^d) where b = branching factor, d = depth.
* **Space complexity**: O(b^d) — frontier can grow exponentially.
* **Data structure**: ``collections.deque`` FIFO queue.

Interface contract
~~~~~~~~~~~~~~~~~~
``bfs(graph, start, goal)`` accepts either a CampusGraph or a GridMap.
The graph must expose:
    get_neighbors(name) -> list[tuple[str, float]]   (CampusGraph)
    get_neighbors_by_name(name) -> list[tuple[str, float]]  (GridMap)

This is handled transparently by ``_get_neighbors``.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Union

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.models import SearchResult


def bfs(
    graph: Union[CampusGraph, GridMap],
    start: str,
    goal: str,
) -> SearchResult:
    """
    Run Breadth-First Search from *start* to *goal*.

    Parameters
    ----------
    graph : CampusGraph | GridMap
        The environment to search.  Must not be modified during search.
    start : str
        Name of the starting node / cell.
    goal : str
        Name of the goal node / cell.

    Returns
    -------
    SearchResult
        Populated with path, cost, counters, and timing.
        ``success=False`` and ``path=[]`` if goal is unreachable.

    Notes
    -----
    *path_cost* is the sum of edge weights along the returned path.
    On a uniform-cost graph (all weights = 1) this equals hop count.
    On a weighted graph it may differ from the minimum-weight path.
    """
    t_start = time.perf_counter()

    # ---- validate inputs ---------------------------------------------------
    try:
        _validate_node(graph, start)
        _validate_node(graph, goal)
    except KeyError as exc:
        elapsed = (time.perf_counter() - t_start) * 1000
        return SearchResult(
            algorithm="BFS",
            start=start,
            goal=goal,
            success=False,
            execution_time_ms=elapsed,
            notes=str(exc),
        )

    # ---- trivial case -------------------------------------------------------
    if start == goal:
        elapsed = (time.perf_counter() - t_start) * 1000
        return SearchResult(
            algorithm="BFS",
            start=start,
            goal=goal,
            path=[start],
            path_cost=0.0,
            nodes_expanded=1,
            nodes_generated=1,
            execution_time_ms=elapsed,
            success=True,
        )

    # ---- BFS ----------------------------------------------------------------
    frontier: deque[str] = deque([start])
    came_from: dict[str, str | None] = {start: None}
    path_costs: dict[str, float] = {start: 0.0}

    nodes_expanded = 0
    nodes_generated = 1  # start node counted as generated

    while frontier:
        current = frontier.popleft()
        nodes_expanded += 1

        for neighbor, weight in _get_neighbors(graph, current):
            if neighbor == goal:
                elapsed = (time.perf_counter() - t_start) * 1000
                came_from[neighbor] = current
                return SearchResult(
                    algorithm="BFS",
                    start=start,
                    goal=goal,
                    path=_reconstruct_path(came_from, neighbor),
                    path_cost=path_costs[current] + weight,
                    nodes_expanded=nodes_expanded,
                    nodes_generated=nodes_generated + 1,
                    execution_time_ms=elapsed,
                    success=True,
                )

            if neighbor not in came_from:
                came_from[neighbor] = current
                path_costs[neighbor] = path_costs[current] + weight
                nodes_generated += 1
                frontier.append(neighbor)

    # ---- goal unreachable ---------------------------------------------------
    elapsed = (time.perf_counter() - t_start) * 1000
    return SearchResult(
        algorithm="BFS",
        start=start,
        goal=goal,
        success=False,
        nodes_expanded=nodes_expanded,
        nodes_generated=nodes_generated,
        execution_time_ms=elapsed,
        notes="Goal is unreachable from start.",
    )


# ---------------------------------------------------------------------------
# Internal helpers (not part of the public API)
# ---------------------------------------------------------------------------

def _get_neighbors(
    graph: Union[CampusGraph, GridMap],
    name: str,
) -> list[tuple[str, float]]:
    """Return [(neighbor_name, weight)] regardless of graph type."""
    if isinstance(graph, GridMap):
        return graph.get_neighbors_by_name(name)
    return graph.get_neighbors(name)


def _validate_node(graph: Union[CampusGraph, GridMap], name: str) -> None:
    """Raise KeyError if *name* is not a valid, walkable node."""
    if isinstance(graph, GridMap):
        try:
            row, col = GridMap.name_to_pos(name)
        except ValueError as exc:
            raise KeyError(str(exc)) from exc
        if not graph.is_valid(row, col):
            raise KeyError(f"Cell '{name}' is an obstacle or out of bounds.")
    else:
        if not graph.has_node(name):
            raise KeyError(f"Node '{name}' not found in graph.")


def _reconstruct_path(came_from: dict[str, str | None], goal: str) -> list[str]:
    """Reconstruct a path from the predecessor map without copying paths in the queue."""
    path: list[str] = []
    current: str | None = goal
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path
