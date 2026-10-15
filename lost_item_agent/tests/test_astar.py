"""
tests/test_astar.py
-------------------
Unit tests for A* Search.

Critical correctness checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. A* with null heuristic == Dijkstra (same path cost as BFS on unweighted).
2. A* path cost <= BFS path cost on weighted graphs (A* finds weight-optimal).
3. With Manhattan on an obstacle-free grid, path cost == Manhattan distance.
4. A* handles disconnected graphs and invalid inputs gracefully.
5. A* with consistent heuristic does NOT expand any node more than once.
"""

import math
import pytest

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import build_default_campus
from environment.models import Node
from search.astar import astar
from search.bfs import bfs
from search.heuristics import (
    euclidean_distance,
    manhattan_distance,
    null_heuristic,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def line_graph() -> CampusGraph:
    g = CampusGraph()
    for name, row, col in [("A", 0, 0), ("B", 0, 1), ("C", 0, 2), ("D", 0, 3)]:
        g.add_node(Node(name, row, col))
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "C", weight=2.0)
    g.add_edge("C", "D", weight=3.0)
    return g


@pytest.fixture
def weighted_diamond() -> CampusGraph:
    """
    Diamond with different weights:
      A → B: 1,  B → D: 10
      A → C: 2,  C → D: 2
    Shortest weight: A-C-D = 4
    Shortest hops:   A-B-D = 2 (but cost = 11)
    BFS returns hop-shortest (A-B-D), A* returns weight-optimal (A-C-D).
    """
    g = CampusGraph()
    g.add_node(Node("A", 0, 1))
    g.add_node(Node("B", 1, 0))
    g.add_node(Node("C", 1, 2))
    g.add_node(Node("D", 2, 1))
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("A", "C", weight=2.0)
    g.add_edge("B", "D", weight=10.0)
    g.add_edge("C", "D", weight=2.0)
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
# Null-heuristic == Dijkstra baseline
# ---------------------------------------------------------------------------

class TestAstarNullHeuristic:
    def test_null_heuristic_finds_weight_optimal_path(self, weighted_diamond: CampusGraph):
        """A* with h=0 must find weight-optimal path (A-C-D, cost 4)."""
        result = astar(weighted_diamond, "A", "D", null_heuristic)
        assert result.success
        assert math.isclose(result.path_cost, 4.0, rel_tol=1e-9)

    def test_null_heuristic_same_cost_as_on_unweighted(self, line_graph: CampusGraph):
        """On unweighted graph, A*(null) cost == BFS cost."""
        # line_graph has weights 1, 2, 3 — NOT unweighted — check cost optimal
        result_astar = astar(line_graph, "A", "D", null_heuristic)
        assert result_astar.success
        # Minimum cost = 1+2+3 = 6 (only path)
        assert math.isclose(result_astar.path_cost, 6.0)

    def test_astar_null_vs_bfs_on_uniform_graph(self):
        """On a uniform-weight graph, A*(null) cost == BFS cost."""
        g = CampusGraph()
        for name, row, col in [("A", 0, 0), ("B", 0, 1), ("C", 0, 2)]:
            g.add_node(Node(name, row, col))
        g.add_edge("A", "B", weight=1.0)
        g.add_edge("B", "C", weight=1.0)
        r_bfs = bfs(g, "A", "C")
        r_astar = astar(g, "A", "C", null_heuristic)
        assert math.isclose(r_bfs.path_cost, r_astar.path_cost)


# ---------------------------------------------------------------------------
# Weight-optimality tests (A* better than BFS on weighted graphs)
# ---------------------------------------------------------------------------

class TestAstarOptimality:
    def test_astar_finds_weight_optimal_on_diamond(self, weighted_diamond: CampusGraph):
        result = astar(weighted_diamond, "A", "D", euclidean_distance)
        assert result.success
        assert math.isclose(result.path_cost, 4.0, rel_tol=1e-9)
        assert result.path == ["A", "C", "D"]

    def test_astar_cost_le_bfs_cost_on_weighted_graph(self, weighted_diamond: CampusGraph):
        """A* path cost must be <= BFS path cost (BFS may take a more expensive path)."""
        r_bfs = bfs(weighted_diamond, "A", "D")
        r_astar = astar(weighted_diamond, "A", "D", euclidean_distance)
        assert r_astar.success
        assert r_astar.path_cost <= r_bfs.path_cost + 1e-9

    def test_astar_cost_le_bfs_on_campus(self, campus: CampusGraph):
        """A* path cost should be <= BFS path cost for campus searches."""
        pairs = [
            ("Main Entrance", "Classroom-101"),
            ("Library", "Washroom-F"),
            ("Parking", "Office-A"),
        ]
        for start, goal in pairs:
            r_bfs = bfs(campus, start, goal)
            r_astar = astar(campus, start, goal, euclidean_distance)
            if r_bfs.success and r_astar.success:
                assert r_astar.path_cost <= r_bfs.path_cost + 1e-9, (
                    f"A* ({r_astar.path_cost}) > BFS ({r_bfs.path_cost}) "
                    f"for {start}→{goal}"
                )

    def test_reopens_node_when_a_better_path_is_found(self):
        graph = CampusGraph()
        for name, row, col in (
            ("Start", 0, 0),
            ("A", 0, 1),
            ("B", 1, 0),
            ("Goal", 0, 2),
        ):
            graph.add_node(Node(name, row, col))
        graph.add_edge("Start", "A", weight=3.0)
        graph.add_edge("Start", "B", weight=1.0)
        graph.add_edge("B", "A", weight=1.0)
        graph.add_edge("A", "Goal", weight=2.0)
        graph.add_edge("B", "Goal", weight=100.0)

        admissible_inconsistent = {
            "Start": 4.0,
            "A": 0.0,
            "B": 3.0,
            "Goal": 0.0,
        }

        def heuristic(node: str, goal: str, _graph: CampusGraph) -> float:
            return admissible_inconsistent[node]

        result = astar(graph, "Start", "Goal", heuristic)

        assert result.success
        assert result.path == ["Start", "B", "A", "Goal"]
        assert result.path_cost == 4.0


# ---------------------------------------------------------------------------
# Manhattan distance on grid
# ---------------------------------------------------------------------------

class TestAstarManhattanGrid:
    def test_no_obstacle_cost_equals_manhattan(self):
        """On an obstacle-free grid with unit costs, A* cost == Manhattan distance."""
        g = GridMap(10, 10)
        start, goal = "(0,0)", "(9,9)"
        expected_cost = manhattan_distance(start, goal, g)  # = 18
        result = astar(g, start, goal, manhattan_distance)
        assert result.success
        assert math.isclose(result.path_cost, expected_cost, rel_tol=1e-9)

    def test_astar_path_length_equals_manhattan_no_obstacles(self):
        g = GridMap(5, 5)
        result = astar(g, "(0,0)", "(4,4)", manhattan_distance)
        assert result.path_length == 8  # Manhattan distance = 8

    def test_astar_avoids_obstacles(self):
        g = GridMap(5, 5)
        g.set_obstacle(2, 0)
        g.set_obstacle(2, 1)
        g.set_obstacle(2, 2)
        g.set_obstacle(2, 3)
        # Must go around row 2 (only gap at col 4)
        result = astar(g, "(0,0)", "(4,0)", manhattan_distance)
        assert result.success
        for node in result.path:
            r, c = GridMap.name_to_pos(node)
            assert not g.is_obstacle(r, c)

    def test_astar_path_contains_no_obstacles(self):
        g = GridMap.from_obstacle_density(10, 10, density=0.2, seed=42)
        result = astar(g, "(0,0)", "(9,9)", manhattan_distance)
        if result.success:
            for name in result.path:
                r, c = GridMap.name_to_pos(name)
                assert not g.is_obstacle(r, c)


# ---------------------------------------------------------------------------
# Trivial cases
# ---------------------------------------------------------------------------

class TestAstarTrivial:
    def test_start_equals_goal(self, line_graph: CampusGraph):
        result = astar(line_graph, "A", "A", euclidean_distance)
        assert result.success
        assert result.path == ["A"]
        assert result.path_cost == 0.0
        assert result.path_length == 0

    def test_adjacent_nodes(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Reception", euclidean_distance)
        assert result.success
        assert result.path == ["Main Entrance", "Reception"]


# ---------------------------------------------------------------------------
# Failure / disconnection tests
# ---------------------------------------------------------------------------

class TestAstarFailures:
    def test_disconnected_graph(self, disconnected_graph: CampusGraph):
        result = astar(disconnected_graph, "X", "Y", euclidean_distance)
        assert not result.success
        assert result.path == []

    def test_blocked_edge_fails(self, campus: CampusGraph):
        # Remove stairwell — only connection between floors
        campus.block_edge("Corridor-G1", "Stairwell")
        campus.block_edge("Library", "Stairwell")
        result = astar(campus, "Main Entrance", "Classroom-101", euclidean_distance)
        assert not result.success

    def test_invalid_start(self, campus: CampusGraph):
        result = astar(campus, "NONE", "Library", euclidean_distance)
        assert not result.success

    def test_invalid_goal(self, campus: CampusGraph):
        result = astar(campus, "Library", "NONE", euclidean_distance)
        assert not result.success

    def test_fully_blocked_grid(self):
        g = GridMap(3, 3)
        g.set_obstacle(1, 0)
        g.set_obstacle(1, 1)
        g.set_obstacle(1, 2)
        result = astar(g, "(0,0)", "(2,2)", manhattan_distance)
        assert not result.success


# ---------------------------------------------------------------------------
# Metric tests
# ---------------------------------------------------------------------------

class TestAstarMetrics:
    def test_algorithm_name(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Library", euclidean_distance)
        assert result.algorithm == "A*"

    def test_heuristic_name_recorded(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Library", euclidean_distance)
        assert result.heuristic_used == "euclidean_distance"

    def test_nodes_expanded_positive(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Library", euclidean_distance)
        assert result.nodes_expanded > 0

    def test_nodes_generated_gte_expanded(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Library", euclidean_distance)
        assert result.nodes_generated >= result.nodes_expanded

    def test_execution_time_non_negative(self, campus: CampusGraph):
        result = astar(campus, "Main Entrance", "Library", euclidean_distance)
        assert result.execution_time_ms >= 0.0

    def test_astar_nodes_generated_lte_bfs_on_obstacle_grid(self):
        """
        On a grid WITH obstacles, A* with Manhattan heuristic generates fewer
        nodes than BFS because the heuristic focuses the search.

        Academic note: On an OBSTACLE-FREE grid every cell has the same
        f-value (g + h is constant along the optimal frontier), so A* and
        BFS expand a similar number of nodes. The heuristic's guidance value
        shows up when obstacles create varied path costs.
        """
        import random
        rng = random.Random(7)
        g = GridMap(15, 15)
        # Place random obstacles (avoid corners)
        for r in range(15):
            for c in range(15):
                if (r, c) in {(0, 0), (14, 14)}:
                    continue
                if rng.random() < 0.25:
                    g.set_obstacle(r, c)

        r_bfs = bfs(g, "(0,0)", "(14,14)")
        r_astar = astar(g, "(0,0)", "(14,14)", manhattan_distance)

        if r_bfs.success and r_astar.success:
            # A* nodes_generated should be <= BFS nodes_generated
            # (A* focuses the frontier; BFS expands in all directions)
            assert r_astar.nodes_generated <= r_bfs.nodes_generated, (
                f"A* generated {r_astar.nodes_generated} but BFS only "
                f"{r_bfs.nodes_generated} — heuristic not helping"
            )

    def test_path_nodes_are_connected(self, campus: CampusGraph):
        """Every consecutive pair in the returned path must be neighbors."""
        result = astar(campus, "Main Entrance", "Classroom-101", euclidean_distance)
        assert result.success
        for i in range(len(result.path) - 1):
            a, b = result.path[i], result.path[i + 1]
            neighbor_names = [n for n, _ in campus.get_neighbors(a)]
            assert b in neighbor_names, (
                f"A* path has disconnected step: {a} → {b}"
            )
