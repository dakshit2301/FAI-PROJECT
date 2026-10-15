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
from typing import TYPE_CHECKING, Union

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
