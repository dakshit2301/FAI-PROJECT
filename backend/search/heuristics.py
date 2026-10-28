"""
search/heuristics.py
--------------------
Heuristic functions for informed search algorithms.

All heuristics share the signature:
    heuristic(node_a: str, node_b: str, map_) -> float

where ``map_`` is either a CampusGraph or a GridMap.

Admissibility guarantee
~~~~~~~~~~~~~~~~~~~~~~~
A heuristic h(n) is *admissible* if it never overestimates the true cost
to reach the goal.  This guarantees that A* returns an optimal solution.

Manhattan distance
    h(n) = |row_n - row_goal| + |col_n - col_goal|
    Admissible for 4-directional movement with uniform edge cost = 1.0.
    Reason: each step moves exactly 1 unit in one axis direction, so the
    minimum cost to cover any Manhattan distance is exactly that distance.

Euclidean distance
    h(n) = sqrt((row_n - row_goal)^2 + (col_n - col_goal)^2)
    Admissible when the minimum edge weight in the graph is >= 1.0
    (Euclidean <= actual path cost for unit-weight graphs).
    Used for the CampusGraph whose minimum edge weight is 1.0.

Null heuristic
    h(n) = 0  for all n
    Always admissible.  Reduces A* to Dijkstra's algorithm (or BFS on
    unweighted uniform-cost graphs).  Useful as a correctness baseline.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Callable, Union

if TYPE_CHECKING:
    from environment.graph import CampusGraph
    from environment.grid import GridMap

MapType = Union["CampusGraph", "GridMap"]


# ---------------------------------------------------------------------------
# Public heuristics
# ---------------------------------------------------------------------------

def manhattan_distance(node_a: str, node_b: str, map_: "GridMap") -> float:
    """
    Manhattan distance between two grid cells.

    Parameters
    ----------
    node_a, node_b : str
        Canonical grid cell names, e.g. ``'(2,3)'``.
    map_ : GridMap
        Used to parse positions from names.

    Returns
    -------
    float
        |row_a - row_b| + |col_a - col_b|

    Notes
    -----
    Admissible and consistent for 4-directional uniform-cost grids.
    Consistency (monotonicity): for any neighbor n' of n reached by one
    step, h(n) <= 1 + h(n'), which holds because one step covers at most
    one unit of Manhattan distance.
    """
    from environment.grid import GridMap as _GridMap
    r_a, c_a = _GridMap.name_to_pos(node_a)
    r_b, c_b = _GridMap.name_to_pos(node_b)
    return float(abs(r_a - r_b) + abs(c_a - c_b))


def euclidean_distance(node_a: str, node_b: str, map_: "CampusGraph") -> float:
    """
    Straight-line (Euclidean) distance between two campus graph nodes.

    Parameters
    ----------
    node_a, node_b : str
        Node names as registered in the CampusGraph.
    map_ : CampusGraph
        Used to retrieve (row, col) positions for each node.

    Returns
    -------
    float
        sqrt((row_a - row_b)^2 + (col_a - col_b)^2)

    Notes
    -----
    Admissible for the default campus graph whose minimum edge weight is 1.0,
    because the straight-line distance is always <= actual path cost.
    """
    na = map_.get_node(node_a)
    nb = map_.get_node(node_b)
    return math.sqrt((na.row - nb.row) ** 2 + (na.col - nb.col) ** 2)


def null_heuristic(node_a: str, node_b: str, map_: MapType) -> float:
    """
    Zero heuristic — always returns 0.

    Using this with A* degrades it to Dijkstra's algorithm (optimal,
    but expands all nodes up to the goal cost frontier).

    Useful as a correctness baseline: A* with h=0 must return the same
    path cost as Dijkstra / BFS on unweighted graphs.
    """
    return 0.0


# ---------------------------------------------------------------------------
# Registry (name → callable) for UI dropdowns
# ---------------------------------------------------------------------------

HEURISTIC_REGISTRY: dict[str, callable] = {
    "manhattan": manhattan_distance,
    "euclidean": euclidean_distance,
    "null (Dijkstra mode)": null_heuristic,
}


# ---------------------------------------------------------------------------
# Admissibility and Consistency Verification
# ---------------------------------------------------------------------------

def verify_heuristic_admissibility_and_consistency(
    graph: MapType,
    heuristic: Callable[[str, str, MapType], float],
    nodes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Empirically and mathematically verify whether a heuristic function is
    admissible and consistent (monotonic) on a given environment.

    Formal Definitions:
    -------------------
    1. Goal condition:
       h(g, g) == 0.0 for all goal states g.

    2. Admissibility:
       h(n, g) <= h*(n, g) for all nodes n and goals g, where h*(n, g) is the
       true minimum path cost from n to g. A heuristic that never overestimates
       the true cost guarantees that A* tree/graph search is cost-optimal.

    3. Consistency (Monotonicity / Triangle Inequality):
       h(u, g) <= c(u, v) + h(v, g) for all directed edges (u, v) and all goals g.
       Every consistent heuristic is also admissible (by induction along optimal paths).
       Consistency guarantees that when A* expands a node, the path found to it is
       already optimal, eliminating the need to reopen closed nodes.

    Parameters
    ----------
    graph : CampusGraph | GridMap
        The search environment.
    heuristic : Callable
        h(node_a, node_b, graph) -> float
    nodes : list[str], optional
        List of node names to verify across. If None, all nodes in graph are used.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
          - "admissible": bool
          - "consistent": bool
          - "goal_condition_valid": bool
          - "pairs_tested": int
          - "edges_tested": int
          - "admissibility_violations": list of dicts describing violations
          - "consistency_violations": list of dicts describing violations
    """
    from search.astar import astar

    if nodes is None:
        if hasattr(graph, "node_names"):
            nodes = graph.node_names()
        elif hasattr(graph, "all_names"):
            nodes = graph.all_names()
        else:
            nodes = []

    goal_valid = True
    admissibility_violations: list[dict[str, Any]] = []
    consistency_violations: list[dict[str, Any]] = []
    pairs_tested = 0
    edges_tested = 0

    # 1. Goal condition check: h(g, g) must be 0
    for g in nodes:
        h_gg = heuristic(g, g, graph)
        if abs(h_gg) > 1e-9:
            goal_valid = False
            admissibility_violations.append({
                "type": "goal_nonzero",
                "node": g,
                "h_value": h_gg,
                "expected": 0.0,
            })

    # 2. Admissibility check: h(n, g) <= actual shortest path cost h*(n, g)
    # We compute true shortest path using A* with the null heuristic (Dijkstra)
    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue
            h_val = heuristic(src, dst, graph)
            if h_val < 0:
                admissibility_violations.append({
                    "type": "negative_heuristic",
                    "src": src,
                    "dst": dst,
                    "h_value": h_val,
                })
            # Compute true shortest path
            result = astar(graph, src, dst, null_heuristic)
            if result.success:
                pairs_tested += 1
                true_cost = result.path_cost
                if h_val > true_cost + 1e-9:
                    admissibility_violations.append({
                        "type": "overestimation",
                        "src": src,
                        "dst": dst,
                        "h_value": round(h_val, 4),
                        "true_cost": round(true_cost, 4),
                        "excess": round(h_val - true_cost, 4),
                    })

    # 3. Consistency check: h(u, g) <= c(u, v) + h(v, g) for all edges (u, v) and all goals g
    # Collect all traversable edges
    edge_list: list[tuple[str, str, float]] = []
    if hasattr(graph, "all_edges"):
        for edge in graph.all_edges():
            if not edge.blocked:
                edge_list.append((edge.source, edge.target, edge.weight))
                edge_list.append((edge.target, edge.source, edge.weight))
    elif hasattr(graph, "get_neighbors_by_name"):
        for u in nodes:
            for v, weight in graph.get_neighbors_by_name(u):
                edge_list.append((u, v, weight))
    elif hasattr(graph, "get_neighbours_by_name"):
        for u in nodes:
            for v, weight in graph.get_neighbours_by_name(u):
                edge_list.append((u, v, weight))

    for u, v, weight in edge_list:
        for g in nodes:
            edges_tested += 1
            h_u = heuristic(u, g, graph)
            h_v = heuristic(v, g, graph)
            if h_u > weight + h_v + 1e-9:
                consistency_violations.append({
                    "u": u,
                    "v": v,
                    "goal": g,
                    "weight": round(weight, 4),
                    "h_u": round(h_u, 4),
                    "h_v": round(h_v, 4),
                    "step_cost_plus_h_v": round(weight + h_v, 4),
                    "violation": round(h_u - (weight + h_v), 4),
                })

    is_admissible = goal_valid and len(admissibility_violations) == 0
    is_consistent = len(consistency_violations) == 0

    return {
        "admissible": is_admissible,
        "consistent": is_consistent,
        "goal_condition_valid": goal_valid,
        "pairs_tested": pairs_tested,
        "edges_tested": edges_tested,
        "admissibility_violations": admissibility_violations,
        "consistency_violations": consistency_violations,
    }

