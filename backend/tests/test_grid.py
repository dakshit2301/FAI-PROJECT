"""
tests/test_grid.py
------------------
Unit tests for GridMap.
"""

import pytest

from environment.grid import GridMap


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_grid() -> GridMap:
    """5×5 obstacle-free grid."""
    return GridMap(5, 5)


@pytest.fixture
def grid_with_obstacle() -> GridMap:
    """5×5 grid with one obstacle at (2,2)."""
    g = GridMap(5, 5)
    g.set_obstacle(2, 2)
    return g


# ---------------------------------------------------------------------------
# Constructor / property tests
# ---------------------------------------------------------------------------

class TestGridMapConstruction:
    def test_dimensions(self, small_grid: GridMap):
        assert small_grid.rows == 5
        assert small_grid.cols == 5

    def test_num_cells(self, small_grid: GridMap):
        assert small_grid.num_cells == 25

    def test_invalid_dimensions(self):
        with pytest.raises(ValueError):
            GridMap(0, 5)
        with pytest.raises(ValueError):
            GridMap(5, 0)

    def test_repr(self, small_grid: GridMap):
        r = repr(small_grid)
        assert "GridMap" in r


# ---------------------------------------------------------------------------
# Obstacle tests
# ---------------------------------------------------------------------------

class TestObstacles:
    def test_set_obstacle(self, small_grid: GridMap):
        small_grid.set_obstacle(1, 1)
        assert small_grid.is_obstacle(1, 1)

    def test_clear_obstacle(self, small_grid: GridMap):
        small_grid.set_obstacle(1, 1)
        small_grid.clear_obstacle(1, 1)
        assert not small_grid.is_obstacle(1, 1)

    def test_clear_non_obstacle_noop(self, small_grid: GridMap):
        """Clearing a cell that is not an obstacle should not raise."""
        small_grid.clear_obstacle(0, 0)

    def test_out_of_bounds_obstacle_raises(self, small_grid: GridMap):
        with pytest.raises(ValueError):
            small_grid.set_obstacle(10, 10)

    def test_obstacle_count(self, grid_with_obstacle: GridMap):
        assert grid_with_obstacle.obstacle_count == 1

    def test_is_valid_free_cell(self, small_grid: GridMap):
        assert small_grid.is_valid(0, 0)

    def test_is_valid_obstacle_cell(self, grid_with_obstacle: GridMap):
        assert not grid_with_obstacle.is_valid(2, 2)

    def test_is_valid_out_of_bounds(self, small_grid: GridMap):
        assert not small_grid.is_valid(-1, 0)
        assert not small_grid.is_valid(0, 5)


# ---------------------------------------------------------------------------
# Neighbour tests
# ---------------------------------------------------------------------------

class TestNeighbours:
    def test_center_has_four_neighbours(self, small_grid: GridMap):
        neighbors = small_grid.get_neighbors(2, 2)
        assert len(neighbors) == 4

    def test_corner_has_two_neighbours(self, small_grid: GridMap):
        neighbors = small_grid.get_neighbors(0, 0)
        assert len(neighbors) == 2

    def test_edge_cell_has_three_neighbours(self, small_grid: GridMap):
        neighbors = small_grid.get_neighbors(0, 2)  # top edge, middle
        assert len(neighbors) == 3

    def test_obstacle_excluded_from_neighbours(self, grid_with_obstacle: GridMap):
        # (2,1) is adjacent to obstacle (2,2)
        neighbors = grid_with_obstacle.get_neighbors(2, 1)
        neighbor_cols = [c for _, c in neighbors]
        assert 2 not in neighbor_cols or all(
            (r, c) != (2, 2) for r, c in neighbors
        )

    def test_obstacle_cell_returns_empty(self, grid_with_obstacle: GridMap):
        assert grid_with_obstacle.get_neighbors(2, 2) == []

    def test_get_neighbours_by_name_returns_tuples(self, small_grid: GridMap):
        nbrs = small_grid.get_neighbors_by_name("(1,1)")
        assert len(nbrs) == 4
        for name, cost in nbrs:
            assert isinstance(name, str)
            assert cost == GridMap.MOVE_COST

    def test_no_diagonal_neighbours(self, small_grid: GridMap):
        """Strictly 4-directional — diagonal cells must never appear."""
        nbrs = small_grid.get_neighbors(1, 1)
        for r, c in nbrs:
            # Only one of row or col should differ
            row_diff = abs(r - 1)
            col_diff = abs(c - 1)
            assert (row_diff + col_diff) == 1, f"Diagonal detected: ({r},{c})"


# ---------------------------------------------------------------------------
# Name / position conversion tests
# ---------------------------------------------------------------------------

class TestNameConversion:
    def test_to_node_name(self):
        assert GridMap.to_node_name(3, 7) == "(3,7)"
        assert GridMap.to_node_name(0, 0) == "(0,0)"

    def test_name_to_pos_roundtrip(self):
        for r in range(5):
            for c in range(5):
                name = GridMap.to_node_name(r, c)
                assert GridMap.name_to_pos(name) == (r, c)

    def test_name_to_pos_bad_format_raises(self):
        with pytest.raises(ValueError):
            GridMap.name_to_pos("not-a-pos")

    def test_all_names_count(self, small_grid: GridMap):
        assert len(small_grid.all_names()) == 25

    def test_all_names_obstacle_excluded(self, grid_with_obstacle: GridMap):
        names = grid_with_obstacle.all_names()
        assert "(2,2)" not in names
        assert len(names) == 24


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestFromObstacleDensity:
    def test_corners_always_clear(self):
        g = GridMap.from_obstacle_density(10, 10, density=0.9, seed=0)
        assert g.is_valid(0, 0)
        assert g.is_valid(9, 9)

    def test_zero_density(self):
        g = GridMap.from_obstacle_density(5, 5, density=0.0, seed=0)
        assert g.obstacle_count == 0

    def test_reproducible_with_same_seed(self):
        g1 = GridMap.from_obstacle_density(10, 10, density=0.3, seed=42)
        g2 = GridMap.from_obstacle_density(10, 10, density=0.3, seed=42)
        assert g1.obstacle_count == g2.obstacle_count
        for r in range(10):
            for c in range(10):
                assert g1.is_obstacle(r, c) == g2.is_obstacle(r, c)

    def test_different_seeds_differ(self):
        g1 = GridMap.from_obstacle_density(10, 10, density=0.3, seed=1)
        g2 = GridMap.from_obstacle_density(10, 10, density=0.3, seed=99)
        # Very unlikely to be identical
        assert g1.obstacle_count != g2.obstacle_count or any(
            g1.is_obstacle(r, c) != g2.is_obstacle(r, c)
            for r in range(10)
            for c in range(10)
        )

    def test_density_clamped(self):
        """Density > 0.9 should be clamped, not raise."""
        g = GridMap.from_obstacle_density(5, 5, density=1.5, seed=0)
        # Corners are always free
        assert g.is_valid(0, 0)

    def test_non_finite_density_raises(self):
        with pytest.raises(ValueError, match="finite"):
            GridMap.from_obstacle_density(5, 5, density=float("nan"))


# ---------------------------------------------------------------------------
# ASCII rendering smoke test
# ---------------------------------------------------------------------------

class TestAsciiRender:
    def test_ascii_dimensions(self, small_grid: GridMap):
        lines = small_grid.to_ascii().split("\n")
        assert len(lines) == 5
        assert all(len(line) == 5 for line in lines)

    def test_obstacle_shown_as_hash(self, grid_with_obstacle: GridMap):
        lines = grid_with_obstacle.to_ascii().split("\n")
        assert lines[2][2] == "#"
