"""
tests/test_heuristics.py
------------------------
Unit tests for heuristic functions.
Tests admissibility properties and numerical correctness.
"""

import math
import pytest

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.models import Node
from environment.locations import build_default_campus
from search.heuristics import (
    manhattan_distance,
    euclidean_distance,
    null_heuristic,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def grid_5x5() -> GridMap:
    return GridMap(5, 5)


@pytest.fixture
def campus() -> CampusGraph:
    return build_default_campus()


# ---------------------------------------------------------------------------
# Manhattan distance tests
# ---------------------------------------------------------------------------

class TestManhattanDistance:
    def test_same_cell_is_zero(self, grid_5x5: GridMap):
        assert manhattan_distance("(2,2)", "(2,2)", grid_5x5) == 0.0

    def test_adjacent_horizontal(self, grid_5x5: GridMap):
        assert manhattan_distance("(0,0)", "(0,1)", grid_5x5) == 1.0

    def test_adjacent_vertical(self, grid_5x5: GridMap):
        assert manhattan_distance("(0,0)", "(1,0)", grid_5x5) == 1.0

    def test_diagonal_cells(self, grid_5x5: GridMap):
        # (0,0) to (3,4): |3-0| + |4-0| = 7
        assert manhattan_distance("(0,0)", "(3,4)", grid_5x5) == 7.0

    def test_symmetry(self, grid_5x5: GridMap):
        a, b = "(1,2)", "(4,0)"
        assert manhattan_distance(a, b, grid_5x5) == manhattan_distance(b, a, grid_5x5)

    def test_never_negative(self, grid_5x5: GridMap):
        assert manhattan_distance("(0,0)", "(4,4)", grid_5x5) >= 0.0

    def test_exact_corner_to_corner_5x5(self, grid_5x5: GridMap):
        # (0,0) → (4,4) = 4 + 4 = 8
        assert manhattan_distance("(0,0)", "(4,4)", grid_5x5) == 8.0


# ---------------------------------------------------------------------------
# Euclidean distance tests
# ---------------------------------------------------------------------------

class TestEuclideanDistance:
    def test_same_node_is_zero(self, campus: CampusGraph):
        assert euclidean_distance("Library", "Library", campus) == 0.0

    def test_symmetry(self, campus: CampusGraph):
        a, b = "Main Entrance", "Library"
        assert math.isclose(
            euclidean_distance(a, b, campus),
            euclidean_distance(b, a, campus),
        )

    def test_never_negative(self, campus: CampusGraph):
        assert euclidean_distance("Main Entrance", "Classroom-101", campus) >= 0.0

    def test_adjacent_nodes_distance(self, campus: CampusGraph):
        # Main Entrance (0,0) → Reception (0,1): distance = 1.0
        d = euclidean_distance("Main Entrance", "Reception", campus)
        assert math.isclose(d, 1.0, rel_tol=1e-9)

    def test_diagonal_nodes(self, campus: CampusGraph):
        # Main Entrance (0,0) → Library (2,0): row diff = 2, col diff = 0
        d = euclidean_distance("Main Entrance", "Library", campus)
        assert math.isclose(d, 2.0, rel_tol=1e-9)

    def test_admissibility_vs_graph_path(self, campus: CampusGraph):
        """
        Euclidean distance must be <= actual path cost for all node pairs.
        Tests admissibility empirically on the default campus.
        """
        from search.astar import astar
        from search.heuristics import null_heuristic

        nodes = campus.node_names()
        for src in nodes:
            for dst in nodes:
                if src == dst:
                    continue
                h = euclidean_distance(src, dst, campus)
                # Get actual shortest path cost via A* with null heuristic
                result = astar(campus, src, dst, null_heuristic)
                if result.success:
                    assert h <= result.path_cost + 1e-9, (
                        f"Inadmissible: h({src},{dst})={h:.3f} > "
                        f"actual_cost={result.path_cost:.3f}"
                    )


# ---------------------------------------------------------------------------
# Null heuristic tests
# ---------------------------------------------------------------------------

class TestNullHeuristic:
    def test_always_zero_grid(self, grid_5x5: GridMap):
        assert null_heuristic("(0,0)", "(4,4)", grid_5x5) == 0.0

    def test_always_zero_graph(self, campus: CampusGraph):
        assert null_heuristic("Library", "Canteen", campus) == 0.0

    def test_same_node_zero(self, grid_5x5: GridMap):
        assert null_heuristic("(2,2)", "(2,2)", grid_5x5) == 0.0
