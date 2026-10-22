"""
environment/models.py
---------------------
Shared domain dataclasses used by every other module.

These are the ONLY canonical definitions of Node, Edge, and SearchResult.
No other module should re-define these structures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Node:
    """
    A single location in the campus environment.

    Parameters
    ----------
    name : str
        Human-readable unique identifier, e.g. ``"Library"`` or ``"Lab-A"``.
    row : int
        Grid row index (0-indexed, top = 0).
    col : int
        Grid column index (0-indexed, left = 0).
    node_type : str
        Category string: ``"classroom"``, ``"lab"``, ``"corridor"``,
        ``"library"``, ``"canteen"``, ``"office"``, ``"washroom"``,
        ``"parking"``, or ``"generic"``.
    search_cost : float
        Effort required to physically search this location on a 1–5 scale.
        1.0 = small, easy-to-search room; 5.0 = large cluttered space.
    """

    name: str
    row: int
    col: int
    node_type: str = "generic"
    search_cost: float = 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.search_cost) or self.search_cost < 0:
            raise ValueError(
                f"search_cost must be finite and >= 0, got {self.search_cost}"
            )
        if self.row < 0 or self.col < 0:
            raise ValueError(
                f"row and col must be >= 0, got row={self.row}, col={self.col}"
            )

    @property
    def position(self) -> tuple[int, int]:
        """Return (row, col) tuple."""
        return (self.row, self.col)


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------

@dataclass
class Edge:
    """
    A traversable corridor between two nodes.

    The graph is undirected: an Edge from A→B implies traversal from B→A
    at the same weight.  The graph layer is responsible for storing both
    directions when needed.

    Parameters
    ----------
    source : str
        Name of the origin Node.
    target : str
        Name of the destination Node.
    weight : float
        Travel cost (distance, time, or difficulty).  Must be > 0.
    blocked : bool
        When True the edge is impassable (e.g. locked door, flooded corridor).
    """

    source: str
    target: str
    weight: float = 1.0
    blocked: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.weight) or self.weight <= 0:
            raise ValueError(f"Edge weight must be finite and > 0, got {self.weight}")


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    """
    The complete output of a single search run.

    All search functions (bfs, greedy_best_first, astar) return this object.
    Consumers of search results must use this type — never ad-hoc dicts.

    Parameters
    ----------
    algorithm : str
        One of ``"BFS"``, ``"Greedy"``, ``"A*"``.
    start : str
        Name of the start node.
    goal : str
        Name of the goal node.
    path : list[str]
        Ordered node names from start to goal.  Empty list if unreachable.
    path_cost : float
        Sum of edge weights along the path.  0.0 if unreachable or start==goal.
    nodes_expanded : int
        Number of nodes popped from the frontier (main loop iterations).
    nodes_generated : int
        Number of nodes placed on the frontier (neighbours enqueued).
    execution_time_ms : float
        Real wall-clock time measured by ``time.perf_counter()``, in
        milliseconds.  Does NOT include UI or I/O time.
    success : bool
        True if a path was found; False if the goal is unreachable.
    heuristic_used : Optional[str]
        Name of the heuristic function, e.g. ``"manhattan"`` or
        ``"euclidean"``.  None for BFS (no heuristic).
    notes : str
        Free-text field for warnings or diagnostic information.
    """

    algorithm: str
    start: str
    goal: str
    path: list[str] = field(default_factory=list)
    path_cost: float = 0.0
    nodes_expanded: int = 0
    nodes_generated: int = 0
    execution_time_ms: float = 0.0
    success: bool = False
    heuristic_used: Optional[str] = None
    notes: str = ""
    explored_nodes: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def path_length(self) -> int:
        """Number of hops (edges) in the path.  0 if no path."""
        return max(0, len(self.path) - 1)

    def summary_dict(self) -> dict:
        """Return a flat dict suitable for pandas / CSV export."""
        return {
            "algorithm": self.algorithm,
            "start": self.start,
            "goal": self.goal,
            "success": self.success,
            "path_length": self.path_length,
            "path_cost": self.path_cost,
            "nodes_expanded": self.nodes_expanded,
            "nodes_generated": self.nodes_generated,
            "execution_time_ms": self.execution_time_ms,
            "heuristic_used": self.heuristic_used or "none",
            "notes": self.notes,
            "explored_nodes": self.explored_nodes,
        }
