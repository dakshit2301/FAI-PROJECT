"""
environment/locations.py
------------------------
Default campus layout definition.

This module defines ``build_default_campus()`` which returns a fully
configured CampusGraph with realistic locations, corridors, and weights.

The campus is a two-floor building with the following zones:

  Ground Floor (row 0–2)
  ├── Main Entrance (0,0)
  ├── Reception (0,1)
  ├── Canteen (0,2)
  ├── Washroom-G (0,3)
  ├── Corridor-G1 (1,0)
  ├── Corridor-G2 (1,1)
  ├── Corridor-G3 (1,2)
  ├── Library (2,0)
  ├── Lab-A (2,1)
  ├── Lab-B (2,2)
  └── Parking (2,3)

  First Floor (row 3–5)
  ├── Stairwell (3,0) — connects floors
  ├── Corridor-F1 (3,1)
  ├── Corridor-F2 (3,2)
  ├── Classroom-101 (4,0)
  ├── Classroom-102 (4,1)
  ├── Classroom-103 (4,2)
  ├── Office-A (5,0)
  ├── Office-B (5,1)
  └── Washroom-F (5,2)

Edge weights reflect approximate walking time (arbitrary units).
"""

from __future__ import annotations

from environment.graph import CampusGraph
from environment.models import Node

# ---------------------------------------------------------------------------
# Node catalogue — (name, row, col, node_type, search_cost)
# ---------------------------------------------------------------------------

_NODES: list[tuple[str, int, int, str, float]] = [
    # --- Ground Floor ---
    ("Main Entrance",  0, 0, "corridor",  1.0),
    ("Reception",      0, 1, "office",    1.5),
    ("Canteen",        0, 2, "canteen",   2.0),
    ("Washroom-G",     0, 3, "washroom",  1.0),
    ("Corridor-G1",    1, 0, "corridor",  1.0),
    ("Corridor-G2",    1, 1, "corridor",  1.0),
    ("Corridor-G3",    1, 2, "corridor",  1.0),
    ("Library",        2, 0, "library",   4.0),
    ("Lab-A",          2, 1, "lab",       3.0),
    ("Lab-B",          2, 2, "lab",       3.0),
    ("Parking",        2, 3, "parking",   2.5),
    # --- First Floor ---
    ("Stairwell",      3, 0, "corridor",  1.0),
    ("Corridor-F1",    3, 1, "corridor",  1.0),
    ("Corridor-F2",    3, 2, "corridor",  1.0),
    ("Classroom-101",  4, 0, "classroom", 2.0),
    ("Classroom-102",  4, 1, "classroom", 2.0),
    ("Classroom-103",  4, 2, "classroom", 2.0),
    ("Office-A",       5, 0, "office",    1.5),
    ("Office-B",       5, 1, "office",    1.5),
    ("Washroom-F",     5, 2, "washroom",  1.0),
]

# ---------------------------------------------------------------------------
# Edge catalogue — (source, target, weight)
# ---------------------------------------------------------------------------

_EDGES: list[tuple[str, str, float]] = [
    # Ground floor horizontal
    ("Main Entrance", "Reception",    1.0),
    ("Reception",     "Canteen",      1.0),
    ("Canteen",       "Washroom-G",   1.0),

    # Ground floor vertical (entrance row ↔ corridor row)
    ("Main Entrance", "Corridor-G1",  1.0),
    ("Reception",     "Corridor-G2",  1.0),
    ("Canteen",       "Corridor-G3",  1.0),

    # Corridor-G row horizontal
    ("Corridor-G1",   "Corridor-G2",  1.0),
    ("Corridor-G2",   "Corridor-G3",  1.0),

    # Corridor-G row ↔ service row
    ("Corridor-G1",   "Library",      1.5),
    ("Corridor-G2",   "Lab-A",        1.5),
    ("Corridor-G3",   "Lab-B",        1.5),
    ("Corridor-G3",   "Parking",      2.0),
    ("Washroom-G",    "Parking",      2.0),

    # Library ↔ Lab-A
    ("Library",       "Lab-A",        1.0),
    ("Lab-A",         "Lab-B",        1.0),

    # Stairwell connects floors
    ("Corridor-G1",   "Stairwell",    2.0),
    ("Library",       "Stairwell",    2.5),

    # First floor
    ("Stairwell",     "Corridor-F1",  1.0),
    ("Corridor-F1",   "Corridor-F2",  1.0),
    ("Stairwell",     "Classroom-101", 1.5),
    ("Corridor-F1",   "Classroom-102", 1.5),
    ("Corridor-F2",   "Classroom-103", 1.5),
    ("Classroom-101", "Office-A",      1.0),
    ("Classroom-102", "Office-B",      1.0),
    ("Classroom-103", "Washroom-F",    1.0),
    ("Office-A",      "Office-B",      1.0),
]


def build_default_campus() -> CampusGraph:
    """
    Construct and return the default campus CampusGraph.

    Every call returns a fresh instance — safe for parallel benchmark runs.
    """
    g = CampusGraph()

    for name, row, col, node_type, search_cost in _NODES:
        g.add_node(Node(
            name=name,
            row=row,
            col=col,
            node_type=node_type,
            search_cost=search_cost,
        ))

    for source, target, weight in _EDGES:
        g.add_edge(source, target, weight=weight)

    return g


def location_names() -> list[str]:
    """Return the list of all default campus location names."""
    return [name for name, *_ in _NODES]


def locations_by_type(node_type: str) -> list[str]:
    """Return location names filtered by node_type."""
    return [name for name, _, _, t, _ in _NODES if t == node_type]


# Convenience: item-type → likely candidate locations mapping
# (user-supplied beliefs — NOT AI-learned probabilities)
ITEM_TYPE_CANDIDATES: dict[str, list[str]] = {
    "laptop":     ["Library", "Lab-A", "Lab-B", "Classroom-101", "Classroom-102", "Classroom-103"],
    "bag":        ["Canteen", "Library", "Classroom-101", "Classroom-102", "Parking"],
    "water bottle":["Canteen", "Corridor-G1", "Washroom-G", "Washroom-F"],
    "keys":       ["Parking", "Reception", "Canteen", "Office-A", "Office-B"],
    "phone":      ["Canteen", "Library", "Classroom-101", "Lab-A", "Office-A"],
    "books":      ["Library", "Classroom-101", "Classroom-102", "Classroom-103"],
    "calculator": ["Classroom-101", "Classroom-102", "Classroom-103", "Lab-A", "Lab-B"],
    "jacket":     ["Canteen", "Library", "Classroom-101", "Corridor-G1", "Parking"],
}
