"""
tests/test_greedy.py
--------------------
Unit tests for Greedy Best-First Search.
"""

import pytest

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import build_default_campus
from environment.models import Node
from search.astar import astar
from search.greedy import greedy_best_first
from search.heuristics import euclidean_distance, manhattan_distance, null_heuristic


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def line_graph() -> CampusGraph:
    g = CampusGraph()
    for name, row, col in [("A", 0, 0), ("B", 0, 1), ("C", 0, 2), ("D", 0, 3)]:
        g.add_node(Node(name, row, col))
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "D")
    return g


@pytest.fixture
def disconnected_graph() -> CampusGraph:
    g = CampusGraph()
    g.add_node(Node("X", 0, 0))
    g.add_node(Node("Y", 0, 1))
    return g


@pytest.fixture
def campus() -> CampusGraph:
    return build_default_campus()


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------

class TestGreedyCorrectness:
    def test_finds_path_on_line_graph(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "A", "D", euclidean_distance)
        assert result.success
        assert result.path[0] == "A"
        assert result.path[-1] == "D"

    def test_start_equals_goal(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "B", "B", euclidean_distance)
        assert result.success
        assert result.path == ["B"]
        assert result.path_cost == 0.0

    def test_algorithm_name(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "A", "D", euclidean_distance)
        assert result.algorithm == "Greedy"

    def test_heuristic_name_recorded(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "A", "D", euclidean_distance)
        assert result.heuristic_used == "euclidean_distance"

    def test_path_valid_start_end(self, campus: CampusGraph):
        result = greedy_best_first(
            campus, "Main Entrance", "Classroom-101", euclidean_distance
        )
        assert result.success
        assert result.path[0] == "Main Entrance"
        assert result.path[-1] == "Classroom-101"


# ---------------------------------------------------------------------------
# Greedy non-optimality demonstration
# ---------------------------------------------------------------------------

class TestGreedyNonOptimality:
    def test_greedy_may_not_be_optimal(self):
        """
        Build a graph where Greedy is misled by the heuristic.

        Layout (row, col):
          S(0,0) --1-- A(0,3) --1-- G(0,6)   [Greedy target: A looks close]
          S(0,0) --1-- B(0,1) --1-- G(0,6)   [actual shorter path by heuristic]

        With euclidean heuristic to G(0,6):
          h(A) = 3.0,  h(B) = 5.0
        Greedy expands A first, which leads to G in 2 steps.
        BFS would also find it in 2 steps here.

        The important property to document: Greedy CAN return a non-optimal
        path on obstacle graphs, but on an open graph like this one it happens
        to be fine.  We verify it always FINDS a path (completeness).
        """
        g = CampusGraph()
        g.add_node(Node("S", 0, 0))
        g.add_node(Node("A", 0, 3))
        g.add_node(Node("B", 0, 1))
        g.add_node(Node("G", 0, 6))
        g.add_edge("S", "A", weight=1.0)
        g.add_edge("S", "B", weight=1.0)
        g.add_edge("A", "G", weight=1.0)
        g.add_edge("B", "G", weight=1.0)

        result = greedy_best_first(g, "S", "G", euclidean_distance)
        assert result.success
        assert result.path[-1] == "G"

    def test_greedy_suboptimal_path_documented(self):
        """
        Maze where Greedy goes in a long direction before backtracking.
        Verifies that Greedy finds A path (completeness) but we do NOT
        assert it's the shortest.
        """
        g = GridMap(5, 5)
        # Block a corridor that looks attractive to a greedy heuristic
        g.set_obstacle(0, 2)
        g.set_obstacle(1, 2)
        g.set_obstacle(2, 2)
        # Path must go around: (0,0)→(4,4)
        result = greedy_best_first(g, "(0,0)", "(4,4)", manhattan_distance)
        assert result.success
        # We do NOT assert path_length == 8 (it may be longer)
        assert result.path[0] == "(0,0)"
        assert result.path[-1] == "(4,4)"

    def test_greedy_can_return_a_costlier_path_than_astar(self):
        graph = CampusGraph()
        for node in (
            Node("Start", 0, 2),
            Node("Near", 0, 1),
            Node("Detour", 1, 2),
            Node("Goal", 0, 0),
        ):
            graph.add_node(node)

        graph.add_edge("Start", "Near", weight=1.0)
        graph.add_edge("Near", "Goal", weight=100.0)
        graph.add_edge("Start", "Detour", weight=1.0)
        graph.add_edge("Detour", "Goal", weight=3.0)

        greedy_result = greedy_best_first(
            graph, "Start", "Goal", euclidean_distance
        )
        astar_result = astar(graph, "Start", "Goal", euclidean_distance)

        assert greedy_result.success and astar_result.success
        assert greedy_result.path == ["Start", "Near", "Goal"]
        assert greedy_result.path_cost == 101.0
        assert astar_result.path == ["Start", "Detour", "Goal"]
        assert astar_result.path_cost == 4.0


# ---------------------------------------------------------------------------
# Failure tests
# ---------------------------------------------------------------------------

class TestGreedyFailures:
    def test_disconnected_returns_failure(self, disconnected_graph: CampusGraph):
        result = greedy_best_first(
            disconnected_graph, "X", "Y", euclidean_distance
        )
        assert not result.success
        assert result.path == []

    def test_invalid_start(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "NONE", "D", euclidean_distance)
        assert not result.success

    def test_invalid_goal(self, line_graph: CampusGraph):
        result = greedy_best_first(line_graph, "A", "NONE", euclidean_distance)
        assert not result.success

    def test_all_obstacle_grid(self):
        g = GridMap(3, 3)
        g.set_obstacle(0, 1)
        g.set_obstacle(1, 0)
        g.set_obstacle(1, 1)
        g.set_obstacle(1, 2)
        g.set_obstacle(2, 1)
        result = greedy_best_first(g, "(0,0)", "(2,2)", manhattan_distance)
        assert not result.success


# ---------------------------------------------------------------------------
# Metric tests
# ---------------------------------------------------------------------------

class TestGreedyMetrics:
    def test_nodes_expanded_positive(self, campus: CampusGraph):
        result = greedy_best_first(
            campus, "Main Entrance", "Library", euclidean_distance
        )
        assert result.nodes_expanded > 0

    def test_execution_time_non_negative(self, campus: CampusGraph):
        result = greedy_best_first(
            campus, "Main Entrance", "Library", euclidean_distance
        )
        assert result.execution_time_ms >= 0.0

    def test_path_cost_positive_on_success(self, campus: CampusGraph):
        result = greedy_best_first(
            campus, "Main Entrance", "Library", euclidean_distance
        )
        assert result.success
        assert result.path_cost > 0.0

    def test_nodes_generated_gte_expanded(self, campus: CampusGraph):
        result = greedy_best_first(
            campus, "Main Entrance", "Classroom-101", euclidean_distance
        )
        assert result.nodes_generated >= result.nodes_expanded


# ---------------------------------------------------------------------------
# Grid Greedy tests
# ---------------------------------------------------------------------------

class TestGreedyOnGrid:
    def test_open_grid_finds_path(self):
        g = GridMap(10, 10)
        result = greedy_best_first(g, "(0,0)", "(9,9)", manhattan_distance)
        assert result.success

    def test_start_goal_same_on_grid(self):
        g = GridMap(5, 5)
        result = greedy_best_first(g, "(2,2)", "(2,2)", manhattan_distance)
        assert result.success
        assert result.path == ["(2,2)"]
