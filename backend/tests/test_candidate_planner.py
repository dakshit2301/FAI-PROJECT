"""
tests/test_candidate_planner.py
--------------------------------
Unit tests for CandidatePlanner.

Test strategy
~~~~~~~~~~~~~
* Verify priority_score ordering is correct.
* Verify unreachable candidates appear last.
* Verify all-unreachable case returns full list with success=False.
* Verify single candidate returns list of one.
* Verify probability_weight affects ranking correctly.
* Verify determinism: same inputs always produce same ranking.
* Verify pathfinding cost vs search cost are correctly separated.
* Verify algorithm field in CandidateResult matches what was chosen.
* Verify visit order is a permutation of the reachable candidates.
* Verify duplicate candidates are deduplicated.
* Verify empty candidate list returns empty list.
"""

import math
import pytest

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import build_default_campus
from environment.models import Node
from planner.candidate_planner import (
    CandidatePlanner,
    CandidateResult,
    DEFAULT_PROBABILITY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def campus() -> CampusGraph:
    return build_default_campus()


@pytest.fixture
def simple_graph() -> CampusGraph:
    """
    Simple graph with 5 nodes.
    Start: Hub (0,0)
    Candidates: Near (0,1), Far (0,5), Isolated (unreachable)

        Hub --1-- Near --1-- Mid --1-- MidFar --1-- Far
                                       (no edge to Isolated)
        Isolated (0,99) — disconnected
    """
    g = CampusGraph()
    g.add_node(Node("Hub",      0, 0, search_cost=1.0))
    g.add_node(Node("Near",     0, 1, search_cost=2.0))
    g.add_node(Node("Mid",      0, 2, search_cost=1.0))
    g.add_node(Node("MidFar",   0, 3, search_cost=1.0))
    g.add_node(Node("Far",      0, 5, search_cost=3.0))
    g.add_node(Node("Isolated", 0, 99, search_cost=1.0))
    g.add_edge("Hub",    "Near",   weight=1.0)
    g.add_edge("Near",   "Mid",    weight=1.0)
    g.add_edge("Mid",    "MidFar", weight=1.0)
    g.add_edge("MidFar", "Far",    weight=1.0)
    # Isolated has no edges
    return g


@pytest.fixture
def planner_bfs(simple_graph: CampusGraph) -> CandidatePlanner:
    return CandidatePlanner(simple_graph, algorithm="bfs")


@pytest.fixture
def planner_astar(simple_graph: CampusGraph) -> CandidatePlanner:
    return CandidatePlanner(simple_graph, algorithm="astar")


# ---------------------------------------------------------------------------
# Basic plan() tests
# ---------------------------------------------------------------------------

class TestPlanBasics:
    def test_unsupported_algorithm_raises(self, campus: CampusGraph):
        with pytest.raises(ValueError, match="Unsupported search algorithm"):
            CandidatePlanner(campus, algorithm="dijkstra")  # type: ignore[arg-type]

    def test_empty_candidates_returns_empty(self, planner_bfs: CandidatePlanner):
        assert planner_bfs.plan("Hub", []) == []

    def test_single_reachable_candidate(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"])
        assert len(results) == 1
        assert results[0].candidate == "Near"
        assert results[0].reachable

    def test_returns_one_result_per_unique_candidate(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Far"])
        assert len(results) == 2

    def test_duplicates_are_deduplicated(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Near", "Far"])
        assert len(results) == 2
        candidates = [r.candidate for r in results]
        assert candidates.count("Near") == 1

    def test_start_equals_candidate(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Hub"])
        assert len(results) == 1
        assert results[0].reachable
        assert results[0].pathfinding_cost == 0.0
        assert results[0].algorithm_result.path == ["Hub"]


# ---------------------------------------------------------------------------
# Ranking / priority tests
# ---------------------------------------------------------------------------

class TestPriorityRanking:
    def test_nearer_candidate_ranked_higher(self, planner_bfs: CandidatePlanner):
        """Near (cost 1+2=3) should rank before Far (cost 4+3=7) at equal prob."""
        results = planner_bfs.plan(
            "Hub",
            ["Far", "Near"],
            probabilities={"Near": 0.5, "Far": 0.5},
        )
        # Both at 0.5 prob → priority_score = total_cost * 0.5
        # Near: (1.0 + 2.0) * 0.5 = 1.5
        # Far:  (4.0 + 3.0) * 0.5 = 3.5
        assert results[0].candidate == "Near"
        assert results[1].candidate == "Far"

    def test_high_probability_raises_rank(self, planner_bfs: CandidatePlanner):
        """
        Near has lower path cost but Far has higher probability.
        With high enough probability on Far, Far should be searched first.

        Near: pathfinding=1, search_cost=2, total=3, prob=0.1 → score=3*0.9=2.7
        Far:  pathfinding=4, search_cost=3, total=7, prob=0.95 → score=7*0.05=0.35
        """
        results = planner_bfs.plan(
            "Hub",
            ["Near", "Far"],
            probabilities={"Near": 0.1, "Far": 0.95},
        )
        assert results[0].candidate == "Far"

    def test_ranks_are_sequential_from_one(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Mid", "Far"])
        ranks = [r.rank for r in results]
        assert ranks == [1, 2, 3]

    def test_unreachable_candidates_last(self, planner_bfs: CandidatePlanner):
        """Isolated is unreachable → must appear after all reachable candidates."""
        results = planner_bfs.plan("Hub", ["Near", "Isolated", "Far"])
        reachable = [r for r in results if r.reachable]
        unreachable = [r for r in results if not r.reachable]
        # All reachable must appear before any unreachable
        last_reachable_rank = max(r.rank for r in reachable)
        first_unreachable_rank = min(r.rank for r in unreachable)
        assert last_reachable_rank < first_unreachable_rank

    def test_all_unreachable(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Isolated"])
        assert len(results) == 1
        assert not results[0].reachable
        assert results[0].priority_score == math.inf

    def test_priority_score_formula(self, planner_bfs: CandidatePlanner):
        """
        Verify priority_score = total_cost × (1 - probability).
        Near: pathfinding=1.0, search_cost=2.0, total=3.0, prob=0.3
        Expected score = 3.0 × 0.7 = 2.1
        """
        results = planner_bfs.plan("Hub", ["Near"], probabilities={"Near": 0.3})
        cr = results[0]
        expected = (cr.pathfinding_cost + cr.search_cost) * (1.0 - 0.3)
        assert abs(cr.priority_score - expected) < 1e-9

    @pytest.mark.parametrize("probability", [float("nan"), float("inf")])
    def test_non_finite_probability_is_rejected(
        self, planner_bfs: CandidatePlanner, probability: float
    ):
        with pytest.raises(ValueError, match="must be finite"):
            planner_bfs.plan("Hub", ["Near"], {"Near": probability})


# ---------------------------------------------------------------------------
# Cost separation tests
# ---------------------------------------------------------------------------

class TestCostSeparation:
    def test_pathfinding_cost_matches_algorithm(self, planner_bfs: CandidatePlanner):
        """pathfinding_cost must equal the path cost returned by the algorithm."""
        results = planner_bfs.plan("Hub", ["Far"])
        cr = results[0]
        assert abs(cr.pathfinding_cost - cr.algorithm_result.path_cost) < 1e-9

    def test_search_cost_from_node(self, planner_bfs: CandidatePlanner, simple_graph: CampusGraph):
        """search_cost must equal Node.search_cost for campus nodes."""
        results = planner_bfs.plan("Hub", ["Near"])
        cr = results[0]
        expected_sc = simple_graph.get_node("Near").search_cost
        assert abs(cr.search_cost - expected_sc) < 1e-9

    def test_total_cost_equals_sum(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Far"])
        cr = results[0]
        assert abs(cr.total_cost - (cr.pathfinding_cost + cr.search_cost)) < 1e-9

    def test_unreachable_has_inf_pathfinding_cost(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Isolated"])
        assert math.isinf(results[0].pathfinding_cost)


# ---------------------------------------------------------------------------
# Algorithm field tests
# ---------------------------------------------------------------------------

class TestAlgorithmField:
    def test_bfs_result_algorithm_name(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"])
        assert results[0].algorithm_result.algorithm == "BFS"

    def test_astar_result_algorithm_name(self, planner_astar: CandidatePlanner):
        results = planner_astar.plan("Hub", ["Near"])
        assert results[0].algorithm_result.algorithm == "A*"

    def test_planner_algorithm_name(self, planner_bfs: CandidatePlanner):
        assert planner_bfs.algorithm_name() == "BFS"

    def test_planner_astar_algorithm_name(self, planner_astar: CandidatePlanner):
        assert planner_astar.algorithm_name() == "A*"


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_inputs_same_output(self, simple_graph: CampusGraph):
        """Two identical calls must return identical rankings."""
        p = CandidatePlanner(simple_graph, algorithm="bfs")
        r1 = p.plan("Hub", ["Near", "Mid", "Far", "Isolated"])
        r2 = p.plan("Hub", ["Near", "Mid", "Far", "Isolated"])
        assert [r.candidate for r in r1] == [r.candidate for r in r2]
        assert [r.priority_score for r in r1] == [r.priority_score for r in r2]

    def test_input_order_irrelevant_to_ranking(self, simple_graph: CampusGraph):
        """Shuffled input order must not change the ranked output order."""
        p = CandidatePlanner(simple_graph, algorithm="bfs")
        r1 = p.plan("Hub", ["Near", "Far"], probabilities={"Near": 0.5, "Far": 0.5})
        r2 = p.plan("Hub", ["Far", "Near"], probabilities={"Near": 0.5, "Far": 0.5})
        assert [r.candidate for r in r1] == [r.candidate for r in r2]


# ---------------------------------------------------------------------------
# Recommended visit order tests
# ---------------------------------------------------------------------------

class TestVisitOrder:
    def test_visit_order_is_permutation_of_reachable(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Far", "Mid"])
        order = planner_bfs.recommended_visit_order(results)
        reachable_names = {r.candidate for r in results if r.reachable}
        assert set(order) == reachable_names

    def test_single_candidate_visit_order(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"])
        order = planner_bfs.recommended_visit_order(results)
        assert order == ["Near"]

    def test_all_unreachable_returns_empty_order(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Isolated"])
        order = planner_bfs.recommended_visit_order(results)
        assert order == []

    def test_visit_order_no_duplicates(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Far", "Mid"])
        order = planner_bfs.recommended_visit_order(results)
        assert len(order) == len(set(order))

    def test_visit_order_excludes_unreachable(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near", "Isolated"])
        order = planner_bfs.recommended_visit_order(results)
        assert "Isolated" not in order


# ---------------------------------------------------------------------------
# Probability clamping tests
# ---------------------------------------------------------------------------

class TestProbabilityClamping:
    def test_probability_above_1_clamped(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"], probabilities={"Near": 2.0})
        assert results[0].probability_weight == 1.0
        # priority_score = total_cost * (1 - 1.0) = 0.0
        assert results[0].priority_score == 0.0

    def test_probability_below_0_clamped(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"], probabilities={"Near": -0.5})
        assert results[0].probability_weight == 0.0
        # priority_score = total_cost * 1.0
        assert abs(results[0].priority_score - results[0].total_cost) < 1e-9

    def test_missing_probability_defaults(self, planner_bfs: CandidatePlanner):
        results = planner_bfs.plan("Hub", ["Near"])  # no prob supplied
        assert results[0].probability_weight == DEFAULT_PROBABILITY


# ---------------------------------------------------------------------------
# Grid-based planner tests
# ---------------------------------------------------------------------------

class TestGridPlanner:
    def test_grid_planner_finds_path(self):
        g = GridMap(5, 5)
        planner = CandidatePlanner(g, algorithm="astar")
        results = planner.plan("(0,0)", ["(4,4)", "(2,2)"])
        assert len(results) == 2
        reachable = [r for r in results if r.reachable]
        assert len(reachable) == 2

    def test_grid_planner_obstacle_makes_unreachable(self):
        g = GridMap(3, 3)
        g.set_obstacle(0, 1)
        g.set_obstacle(1, 0)
        g.set_obstacle(1, 1)
        # (0,0) is completely surrounded
        planner = CandidatePlanner(g, algorithm="bfs")
        results = planner.plan("(0,0)", ["(2,2)"])
        assert not results[0].reachable

    def test_grid_planner_uses_manhattan_by_default(self):
        g = GridMap(5, 5)
        planner = CandidatePlanner(g, algorithm="astar")
        # Verify it doesn't crash and produces a valid result
        results = planner.plan("(0,0)", ["(4,4)"])
        assert results[0].reachable


# ---------------------------------------------------------------------------
# Campus integration tests
# ---------------------------------------------------------------------------

class TestCampusPlanner:
    def test_campus_planner_basic(self, campus: CampusGraph):
        planner = CandidatePlanner(campus, algorithm="astar")
        results = planner.plan(
            "Main Entrance",
            ["Library", "Canteen", "Lab-A"],
        )
        assert len(results) == 3
        for r in results:
            assert r.reachable

    def test_campus_planner_all_nodes_reachable(self, campus: CampusGraph):
        from environment.locations import location_names
        planner = CandidatePlanner(campus, algorithm="bfs")
        candidates = location_names()
        results = planner.plan("Main Entrance", candidates)
        reachable = [r for r in results if r.reachable]
        # All 20 campus nodes reachable from Main Entrance
        assert len(reachable) == 20

    def test_campus_planner_summary_dict(self, campus: CampusGraph):
        planner = CandidatePlanner(campus, algorithm="bfs")
        results = planner.plan("Main Entrance", ["Library"])
        d = results[0].summary_dict()
        required_keys = {
            "rank", "candidate", "reachable", "pathfinding_cost",
            "search_cost", "total_cost", "probability_weight",
            "priority_score", "path_length", "nodes_expanded",
            "execution_time_ms",
        }
        assert required_keys.issubset(d.keys())

    def test_campus_item_type_scenario(self, campus: CampusGraph):
        """Simulates a 'lost laptop' scenario from the locations module."""
        from environment.locations import ITEM_TYPE_CANDIDATES
        candidates = ITEM_TYPE_CANDIDATES["laptop"]
        planner = CandidatePlanner(campus, algorithm="astar")
        results = planner.plan(
            "Main Entrance",
            candidates,
            probabilities={"Library": 0.6, "Lab-A": 0.3},
        )
        assert len(results) == len(set(candidates))
        for r in results:
            assert isinstance(r.priority_score, float)


# ---------------------------------------------------------------------------
# Visit Order & Route Recalculation Tests
# ---------------------------------------------------------------------------

class TestVisitOrderAndRecalculation:
    def test_visit_order_empty(self, campus: CampusGraph):
        planner = CandidatePlanner(campus, algorithm="astar")
        order = planner.recommended_visit_order([])
        assert order == []

    def test_visit_order_single(self, campus: CampusGraph):
        planner = CandidatePlanner(campus, algorithm="astar")
        results = planner.plan("Main Entrance", ["Library"])
        order = planner.recommended_visit_order(results)
        assert order == ["Library"]

    def test_visit_order_is_valid_permutation(self, campus: CampusGraph):
        candidates = ["Library", "Canteen", "Lab-A", "Classroom-101"]
        planner = CandidatePlanner(campus, algorithm="astar")
        results = planner.plan("Main Entrance", candidates)
        order = planner.recommended_visit_order(results, start="Main Entrance")
        assert len(order) == len(candidates)
        assert set(order) == set(candidates)

    def test_visit_order_excludes_unreachable(self):
        g = CampusGraph()
        g.add_node(Node("Start", 0, 0))
        g.add_node(Node("ReachableA", 0, 1))
        g.add_node(Node("ReachableB", 0, 2))
        g.add_node(Node("Unreachable", 9, 9))
        g.add_edge("Start", "ReachableA", 1.0)
        g.add_edge("ReachableA", "ReachableB", 1.0)

        planner = CandidatePlanner(g, algorithm="bfs")
        results = planner.plan("Start", ["ReachableA", "ReachableB", "Unreachable"])
        order = planner.recommended_visit_order(results, start="Start")
        assert "Unreachable" not in order
        assert set(order) == {"ReachableA", "ReachableB"}

    def test_route_recalculation_on_blocked_corridor(self, campus: CampusGraph):
        """
        Verify that blocking an edge in the graph dynamically recalculates
        an alternative path to the candidate without crashing.
        """
        planner = CandidatePlanner(campus, algorithm="astar")
        res1 = planner.plan("Main Entrance", ["Library"])
        assert res1[0].reachable
        path1 = res1[0].algorithm_result.path

        # Block the direct corridor from Corridor-G1 to Library
        campus.block_edge("Corridor-G1", "Library")

        # Recalculate route
        res2 = planner.plan("Main Entrance", ["Library"])
        assert res2[0].reachable, "Library should still be reachable via alternative corridor"
        path2 = res2[0].algorithm_result.path

        # The new path should avoid the blocked corridor
        assert path1 != path2
        for i in range(len(path2) - 1):
            pair = {path2[i], path2[i + 1]}
            assert pair != {"Corridor-G1", "Library"}

    def test_mission_replans_from_last_unsuccessful_candidate(
        self, planner_astar: CandidatePlanner
    ):
        results = planner_astar.plan("Hub", ["Near", "Far"])
        order = planner_astar.recommended_visit_order(results, start="Hub")

        steps = planner_astar.execute_mission("Hub", order, actual_location="Far")

        assert [step.candidate for step in steps] == ["Near", "Far"]
        assert [step.item_found for step in steps] == [False, True]
        assert steps[0].from_location == "Hub"
        assert steps[0].algorithm_result.path == ["Hub", "Near"]
        assert steps[1].from_location == "Near"
        assert steps[1].algorithm_result.path == [
            "Near", "Mid", "MidFar", "Far"
        ]

    def test_mission_stops_at_the_actual_item_location(
        self, planner_astar: CandidatePlanner
    ):
        results = planner_astar.plan("Hub", ["Near", "Far"])
        order = planner_astar.recommended_visit_order(results, start="Hub")

        steps = planner_astar.execute_mission("Hub", order, actual_location="Near")

        assert len(steps) == 1
        assert steps[0].item_found
