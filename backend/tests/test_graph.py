"""
tests/test_graph.py
-------------------
Unit tests for CampusGraph and the default campus layout.
"""

import pytest

from environment.graph import CampusGraph
from environment.locations import build_default_campus, location_names
from environment.models import Edge, Node


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_graph() -> CampusGraph:
    """A B-C linear graph with known properties."""
    g = CampusGraph()
    g.add_node(Node("A", 0, 0))
    g.add_node(Node("B", 0, 1))
    g.add_node(Node("C", 0, 2))
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "C", weight=2.0)
    return g


@pytest.fixture
def campus() -> CampusGraph:
    return build_default_campus()


# ---------------------------------------------------------------------------
# Node tests
# ---------------------------------------------------------------------------

class TestNodeModel:
    def test_node_position_property(self):
        n = Node("X", 3, 4)
        assert n.position == (3, 4)

    def test_node_negative_row_raises(self):
        with pytest.raises(ValueError):
            Node("Bad", -1, 0)

    def test_node_negative_col_raises(self):
        with pytest.raises(ValueError):
            Node("Bad", 0, -1)

    def test_node_negative_search_cost_raises(self):
        with pytest.raises(ValueError):
            Node("Bad", 0, 0, search_cost=-1.0)

    @pytest.mark.parametrize("search_cost", [float("nan"), float("inf")])
    def test_non_finite_search_cost_raises(self, search_cost: float):
        with pytest.raises(ValueError, match="finite"):
            Node("Bad", 0, 0, search_cost=search_cost)

    def test_node_frozen(self):
        """Nodes must be immutable (frozen dataclass)."""
        n = Node("A", 0, 0)
        with pytest.raises((AttributeError, TypeError)):
            n.name = "changed"  # type: ignore[misc]


class TestEdgeModel:
    def test_edge_zero_weight_raises(self):
        with pytest.raises(ValueError):
            Edge("A", "B", weight=0.0)

    def test_edge_negative_weight_raises(self):
        with pytest.raises(ValueError):
            Edge("A", "B", weight=-1.0)

    @pytest.mark.parametrize("weight", [float("nan"), float("inf")])
    def test_non_finite_edge_weight_raises(self, weight: float):
        with pytest.raises(ValueError, match="finite"):
            Edge("A", "B", weight=weight)


# ---------------------------------------------------------------------------
# CampusGraph structural tests
# ---------------------------------------------------------------------------

class TestCampusGraphStructure:
    def test_add_and_retrieve_node(self, simple_graph: CampusGraph):
        node = simple_graph.get_node("A")
        assert node.name == "A"

    def test_missing_node_raises(self, simple_graph: CampusGraph):
        with pytest.raises(KeyError):
            simple_graph.get_node("Z")

    def test_has_node(self, simple_graph: CampusGraph):
        assert simple_graph.has_node("A")
        assert not simple_graph.has_node("Z")

    def test_all_nodes_count(self, simple_graph: CampusGraph):
        assert len(simple_graph.all_nodes()) == 3

    def test_len(self, simple_graph: CampusGraph):
        assert len(simple_graph) == 3

    def test_contains(self, simple_graph: CampusGraph):
        assert "A" in simple_graph
        assert "Z" not in simple_graph

    def test_add_edge_unknown_node_raises(self, simple_graph: CampusGraph):
        with pytest.raises(KeyError):
            simple_graph.add_edge("A", "Z")


# ---------------------------------------------------------------------------
# CampusGraph neighbour / edge tests
# ---------------------------------------------------------------------------

class TestCampusGraphEdges:
    def test_undirected_neighbours(self, simple_graph: CampusGraph):
        """A→B edge must be retrievable from both A and B."""
        a_neighbors = dict(simple_graph.get_neighbors("A"))
        b_neighbors = dict(simple_graph.get_neighbors("B"))
        assert "B" in a_neighbors
        assert "A" in b_neighbors

    def test_edge_weight_preserved(self, simple_graph: CampusGraph):
        assert simple_graph.edge_weight("B", "C") == 2.0
        assert simple_graph.edge_weight("C", "B") == 2.0

    def test_has_edge(self, simple_graph: CampusGraph):
        assert simple_graph.has_edge("A", "B")
        assert simple_graph.has_edge("B", "A")
        assert not simple_graph.has_edge("A", "C")

    def test_all_edges_no_duplicates(self, simple_graph: CampusGraph):
        edges = simple_graph.all_edges()
        # A-B and B-C → 2 unique edges
        assert len(edges) == 2

    def test_remove_edge(self, simple_graph: CampusGraph):
        simple_graph.remove_edge("A", "B")
        assert not simple_graph.has_edge("A", "B")
        assert not simple_graph.has_edge("B", "A")

    def test_remove_nonexistent_edge_noop(self, simple_graph: CampusGraph):
        """Removing a missing edge should not raise."""
        simple_graph.remove_edge("A", "C")  # never existed


# ---------------------------------------------------------------------------
# Obstacle / blocking tests
# ---------------------------------------------------------------------------

class TestEdgeBlocking:
    def test_block_edge_removes_from_neighbours(self, simple_graph: CampusGraph):
        simple_graph.block_edge("A", "B")
        a_neighbors = dict(simple_graph.get_neighbors("A"))
        assert "B" not in a_neighbors

    def test_block_is_bidirectional(self, simple_graph: CampusGraph):
        simple_graph.block_edge("A", "B")
        b_neighbors = dict(simple_graph.get_neighbors("B"))
        assert "A" not in b_neighbors

    def test_unblock_restores_edge(self, simple_graph: CampusGraph):
        simple_graph.block_edge("A", "B")
        simple_graph.unblock_edge("A", "B")
        a_neighbors = dict(simple_graph.get_neighbors("A"))
        assert "B" in a_neighbors

    def test_block_missing_edge_raises(self, simple_graph: CampusGraph):
        with pytest.raises(KeyError):
            simple_graph.block_edge("A", "C")


# ---------------------------------------------------------------------------
# Reachability / path tests
# ---------------------------------------------------------------------------

class TestReachability:
    def test_self_reachable(self, simple_graph: CampusGraph):
        assert simple_graph.has_path("A", "A")

    def test_missing_self_node_is_not_reachable(self, simple_graph: CampusGraph):
        with pytest.raises(KeyError, match="missing"):
            simple_graph.has_path("missing", "missing")

    def test_missing_target_raises(self, simple_graph: CampusGraph):
        with pytest.raises(KeyError, match="missing"):
            simple_graph.has_path("A", "missing")

    def test_path_exists(self, simple_graph: CampusGraph):
        assert simple_graph.has_path("A", "C")

    def test_disconnected_after_block(self, simple_graph: CampusGraph):
        simple_graph.block_edge("A", "B")
        # A can no longer reach C (A-B-C, B-C still exists but A-B blocked)
        assert not simple_graph.has_path("A", "C")

    def test_disconnected_components(self):
        g = CampusGraph()
        g.add_node(Node("X", 0, 0))
        g.add_node(Node("Y", 0, 1))
        g.add_node(Node("Z", 0, 2))
        g.add_edge("X", "Y")
        # Z is isolated
        assert not g.has_path("X", "Z")
        assert not g.has_path("Z", "X")

    def test_single_node_reachable(self):
        g = CampusGraph()
        g.add_node(Node("Solo", 0, 0))
        assert g.has_path("Solo", "Solo")


# ---------------------------------------------------------------------------
# Default campus layout tests
# ---------------------------------------------------------------------------

class TestDefaultCampus:
    def test_all_expected_nodes_present(self, campus: CampusGraph):
        for name in location_names():
            assert campus.has_node(name), f"Missing node: {name}"

    def test_node_count(self, campus: CampusGraph):
        assert len(campus) == 20  # 20 defined locations

    def test_library_reachable_from_entrance(self, campus: CampusGraph):
        assert campus.has_path("Main Entrance", "Library")

    def test_classroom_reachable_from_entrance(self, campus: CampusGraph):
        assert campus.has_path("Main Entrance", "Classroom-101")

    def test_all_nodes_reachable_from_entrance(self, campus: CampusGraph):
        """Every location must be reachable from Main Entrance."""
        for name in location_names():
            assert campus.has_path("Main Entrance", name), (
                f"'{name}' is not reachable from Main Entrance"
            )

    def test_adjacency_dict_type(self, campus: CampusGraph):
        adj = campus.to_adjacency_dict()
        assert isinstance(adj, dict)
        for neighbors in adj.values():
            assert isinstance(neighbors, list)
