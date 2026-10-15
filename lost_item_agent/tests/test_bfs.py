"""
tests/test_bfs.py
-----------------
Unit tests for BFS.

Test strategy
~~~~~~~~~~~~~
* Verify correct path on known graphs where we can compute the answer by hand.
* Verify shortest hop count (not necessarily shortest weight).
* Verify failure on disconnected / obstacle graphs.
* Verify metric fields are populated correctly.
"""

import pytest

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import build_default_campus
from environment.models import Node
from search.astar import astar
from search.bfs import bfs
from search.heuristics import null_heuristic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def line_graph() -> CampusGraph:
    """A → B → C → D linear graph, all weights 1."""
    g = CampusGraph()
    for name, row, col in [("A", 0, 0), ("B", 0, 1), ("C", 0, 2), ("D", 0, 3)]:
        g.add_node(Node(name, row, col))
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "D")
    return g


@pytest.fixture
def diamond_graph() -> CampusGraph:
    """
    Diamond:
        A
       / \\
      B   C
       \\ /
        D
    A-B weight=1, A-C weight=3, B-D weight=1, C-D weight=1.
    Shortest hop path: A-B-D (2 hops).
    Shortest weight path: A-B-D (cost 2) vs A-C-D (cost 4).
    BFS returns hop-shortest: A-B-D.
    """
    g = CampusGraph()
    for name, row, col in [("A", 0, 1), ("B", 1, 0), ("C", 1, 2), ("D", 2, 1)]:
        g.add_node(Node(name, row, col))
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("A", "C", weight=3.0)
    g.add_edge("B", "D", weight=1.0)
    g.add_edge("C", "D", weight=1.0)
    return g


@pytest.fixture
def disconnected_graph() -> CampusGraph:
    """Two isolated nodes with no edge between them."""
    g = CampusGraph()
    g.add_node(Node("X", 0, 0))
    g.add_node(Node("Y", 0, 1))
    return g


@pytest.fixture
def campus() -> CampusGraph:
    return build_default_campus()


# ---------------------------------------------------------------------------
# Path correctness tests
# ---------------------------------------------------------------------------

class TestBFSPathCorrectness:
    def test_line_graph_full_path(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.success
        assert result.path == ["A", "B", "C", "D"]

    def test_line_graph_path_length(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.path_length == 3  # 3 hops

    def test_line_graph_adjacent(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "B")
        assert result.success
        assert result.path == ["A", "B"]
        assert result.path_length == 1

    def test_start_equals_goal(self, line_graph: CampusGraph):
        result = bfs(line_graph, "B", "B")
        assert result.success
        assert result.path == ["B"]
        assert result.path_length == 0
        assert result.path_cost == 0.0

    def test_diamond_bfs_finds_2hop_path(self, diamond_graph: CampusGraph):
        """BFS must find the hop-shortest path A→B→D (2 hops)."""
        result = bfs(diamond_graph, "A", "D")
        assert result.success
        assert result.path_length == 2
        # BFS with FIFO: it will expand A, then B and C, then find D via B
        assert result.path[0] == "A"
        assert result.path[-1] == "D"

    def test_reverse_direction(self, line_graph: CampusGraph):
        """Graph is undirected — search from D to A must also work."""
        result = bfs(line_graph, "D", "A")
        assert result.success
        assert result.path[0] == "D"
        assert result.path[-1] == "A"
        assert result.path_length == 3


# ---------------------------------------------------------------------------
# BFS hop-optimality (vs weight-optimality distinction)
# ---------------------------------------------------------------------------

class TestBFSHopOptimality:
    def test_bfs_prefers_hop_shortcut_over_lower_weight_detour(self):
        """BFS minimizes hops, even when a longer route costs less."""
        graph = CampusGraph()
        graph.add_node(Node("Start", 0, 0))
        graph.add_node(Node("Goal", 0, 1))
        graph.add_node(Node("Detour-A", 1, 0))
        graph.add_node(Node("Detour-B", 1, 1))
        graph.add_edge("Start", "Goal", weight=10.0)
        graph.add_edge("Start", "Detour-A", weight=1.0)
        graph.add_edge("Detour-A", "Detour-B", weight=1.0)
        graph.add_edge("Detour-B", "Goal", weight=1.0)

        bfs_result = bfs(graph, "Start", "Goal")
        astar_result = astar(graph, "Start", "Goal", null_heuristic)

        assert bfs_result.path == ["Start", "Goal"]
        assert bfs_result.path_length == 1
        assert bfs_result.path_cost == 10.0
        assert astar_result.path_length == 3
        assert astar_result.path_cost == 3.0


# ---------------------------------------------------------------------------
# Failure / disconnection tests
# ---------------------------------------------------------------------------

class TestBFSFailures:
    def test_disconnected_graph_fails(self, disconnected_graph: CampusGraph):
        result = bfs(disconnected_graph, "X", "Y")
        assert not result.success
        assert result.path == []

    def test_blocked_edge_makes_unreachable(self, line_graph: CampusGraph):
        line_graph.block_edge("B", "C")
        result = bfs(line_graph, "A", "D")
        assert not result.success

    def test_invalid_start_node(self, line_graph: CampusGraph):
        result = bfs(line_graph, "NONEXISTENT", "A")
        assert not result.success
        assert "NONEXISTENT" in result.notes or result.notes != ""

    def test_invalid_goal_node(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "NONEXISTENT")
        assert not result.success

    def test_grid_obstacle_blocks_path(self):
        """A wall of obstacles that divides the grid."""
        g = GridMap(3, 3)
        # Block middle column
        g.set_obstacle(0, 1)
        g.set_obstacle(1, 1)
        g.set_obstacle(2, 1)
        result = bfs(g, "(0,0)", "(0,2)")
        assert not result.success


# ---------------------------------------------------------------------------
# Metric tests
# ---------------------------------------------------------------------------

class TestBFSMetrics:
    def test_nodes_expanded_positive(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.nodes_expanded > 0

    def test_nodes_generated_gte_expanded(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.nodes_generated >= result.nodes_expanded

    def test_execution_time_positive(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.execution_time_ms >= 0.0

    def test_algorithm_name(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.algorithm == "BFS"

    def test_no_heuristic_used(self, line_graph: CampusGraph):
        result = bfs(line_graph, "A", "D")
        assert result.heuristic_used is None

    def test_path_cost_matches_weights(self, line_graph: CampusGraph):
        """All edges have weight 1.0, so cost == hops."""
        result = bfs(line_graph, "A", "D")
        assert result.path_cost == 3.0  # 3 edges × 1.0


# ---------------------------------------------------------------------------
# Grid BFS tests
# ---------------------------------------------------------------------------

class TestBFSOnGrid:
    def test_grid_finds_path(self):
        g = GridMap(5, 5)
        result = bfs(g, "(0,0)", "(4,4)")
        assert result.success
        assert result.path[0] == "(0,0)"
        assert result.path[-1] == "(4,4)"

    def test_grid_path_length_minimum(self):
        """On a 5×5 obstacle-free grid: minimum hops (0,0)→(4,4) = 8."""
        g = GridMap(5, 5)
        result = bfs(g, "(0,0)", "(4,4)")
        assert result.path_length == 8  # Manhattan distance = 8

    def test_grid_path_avoids_obstacle(self):
        g = GridMap(3, 3)
        g.set_obstacle(1, 0)
        g.set_obstacle(1, 1)
        # (0,0)→(2,0) forced to go right then down
        result = bfs(g, "(0,0)", "(2,0)")
        assert result.success
        assert "(1,0)" not in result.path
        assert "(1,1)" not in result.path

    def test_grid_start_equals_goal(self):
        g = GridMap(5, 5)
        result = bfs(g, "(2,3)", "(2,3)")
        assert result.success
        assert result.path == ["(2,3)"]

    def test_grid_invalid_obstacle_start(self):
        g = GridMap(5, 5)
        g.set_obstacle(0, 0)
        result = bfs(g, "(0,0)", "(4,4)")
        assert not result.success


# ---------------------------------------------------------------------------
# Campus integration test
# ---------------------------------------------------------------------------

class TestBFSOnCampus:
    def test_entrance_to_library(self, campus: CampusGraph):
        result = bfs(campus, "Main Entrance", "Library")
        assert result.success
        assert result.path[0] == "Main Entrance"
        assert result.path[-1] == "Library"

    def test_entrance_to_classroom(self, campus: CampusGraph):
        result = bfs(campus, "Main Entrance", "Classroom-101")
        assert result.success
        assert result.path[-1] == "Classroom-101"
