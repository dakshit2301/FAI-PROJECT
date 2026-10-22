"""
environment/grid.py
-------------------
GridMap — a rectangular obstacle grid for four-directional search.

Design decisions
~~~~~~~~~~~~~~~~
* Cells are identified both by (row, col) integer coordinates and by the
  canonical name string ``"(row,col)"`` so that the same SearchResult /
  heuristic interface used by CampusGraph works unchanged.
* Four-directional movement only (no diagonals).  This keeps Manhattan
  distance admissible and consistent without any caveats.
* Obstacles are stored in a ``set`` for O(1) membership testing.
* The factory ``from_obstacle_density`` generates reproducible random maps
  using a fixed seed — crucial for fair benchmark comparisons.
"""

from __future__ import annotations

import math
import random
from typing import Iterator


class GridMap:
    """
    A rows×cols rectangular grid with obstacle support.

    Each non-obstacle cell is a node; edges connect 4-directional
    non-obstacle neighbors with uniform weight 1.0.
    """

    MOVE_COST: float = 1.0

    def __init__(self, rows: int, cols: int) -> None:
        if rows < 1 or cols < 1:
            raise ValueError(f"Grid must have at least 1 row and 1 col, got {rows}×{cols}.")
        self._rows = rows
        self._cols = cols
        self._obstacles: set[tuple[int, int]] = set()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def num_cells(self) -> int:
        return self._rows * self._cols

    @property
    def obstacle_count(self) -> int:
        return len(self._obstacles)

    # ------------------------------------------------------------------
    # Obstacle management
    # ------------------------------------------------------------------

    def set_obstacle(self, row: int, col: int) -> None:
        """Mark cell as impassable.  Raises ValueError if out of bounds."""
        self._validate(row, col)
        self._obstacles.add((row, col))

    def clear_obstacle(self, row: int, col: int) -> None:
        """Remove obstacle from cell (no-op if not an obstacle)."""
        self._obstacles.discard((row, col))

    def is_obstacle(self, row: int, col: int) -> bool:
        return (row, col) in self._obstacles

    def is_valid(self, row: int, col: int) -> bool:
        """Return True if (row, col) is in bounds and not an obstacle."""
        return (
            0 <= row < self._rows
            and 0 <= col < self._cols
            and (row, col) not in self._obstacles
        )

    def in_bounds(self, row: int, col: int) -> bool:
        """Return True if (row, col) is within grid bounds (ignoring obstacles)."""
        return 0 <= row < self._rows and 0 <= col < self._cols

    # ------------------------------------------------------------------
    # Neighbour generation (4-directional)
    # ------------------------------------------------------------------

    def get_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        Return walkable 4-directional neighbors of (row, col).

        A neighbor is returned only if it is in bounds AND not an obstacle.
        No diagonal movement.  Returns an empty list for obstacle cells.
        """
        if not self.is_valid(row, col):
            return []
        candidates = [
            (row - 1, col),  # up
            (row + 1, col),  # down
            (row, col - 1),  # left
            (row, col + 1),  # right
        ]
        return [(r, c) for r, c in candidates if self.is_valid(r, c)]

    def get_neighbors_by_name(self, name: str) -> list[tuple[str, float]]:
        """
        Same as ``get_neighbors`` but accepts/returns canonical name strings.

        Returns ``[(neighbor_name, MOVE_COST)]``.
        Compatible with the CampusGraph.get_neighbors interface.
        """
        row, col = self.name_to_pos(name)
        return [
            (self.to_node_name(r, c), self.MOVE_COST)
            for r, c in self.get_neighbors(row, col)
        ]

    # ------------------------------------------------------------------
    # Name ↔ position conversion
    # ------------------------------------------------------------------

    @staticmethod
    def to_node_name(row: int, col: int) -> str:
        """Return canonical string name, e.g. ``'(3,7)'``."""
        return f"({row},{col})"

    @staticmethod
    def name_to_pos(name: str) -> tuple[int, int]:
        """
        Parse ``'(row,col)'`` back to ``(row, col)`` integers.

        Raises ValueError on malformed input.
        """
        try:
            inner = name.strip().lstrip("(").rstrip(")")
            r_str, c_str = inner.split(",")
            return int(r_str.strip()), int(c_str.strip())
        except (ValueError, AttributeError):
            raise ValueError(
                f"Cannot parse grid position from name '{name}'.  "
                "Expected format '(row,col)'."
            )

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def all_cells(self) -> Iterator[tuple[int, int]]:
        """Yield all (row, col) pairs that are NOT obstacles."""
        for r in range(self._rows):
            for c in range(self._cols):
                if (r, c) not in self._obstacles:
                    yield r, c

    def all_names(self) -> list[str]:
        """Return canonical names for all non-obstacle cells."""
        return [self.to_node_name(r, c) for r, c in self.all_cells()]

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_obstacle_density(
        cls,
        rows: int,
        cols: int,
        density: float,
        seed: int = 42,
    ) -> "GridMap":
        """
        Create a GridMap with randomly placed obstacles.

        Parameters
        ----------
        rows, cols : int
            Grid dimensions.
        density : float
            Fraction of cells to mark as obstacles (0.0 – 0.9).
            Clamped to [0.0, 0.9] to ensure at least 10 % passable cells.
        seed : int
            Random seed for reproducibility across benchmark trials.

        Notes
        -----
        The top-left cell (0,0) and bottom-right cell (rows-1, cols-1) are
        always kept clear to guarantee a valid start/goal pair exists.
        """
        if not math.isfinite(density):
            raise ValueError(f"Obstacle density must be finite, got {density!r}.")
        density = max(0.0, min(0.9, density))

        grid = cls(rows, cols)
        rng = random.Random(seed)

        for r in range(rows):
            for c in range(cols):
                # Protect corners
                if (r, c) in {(0, 0), (rows - 1, cols - 1)}:
                    continue
                if rng.random() < density:
                    grid.set_obstacle(r, c)

        return grid

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _validate(self, row: int, col: int) -> None:
        if not self.in_bounds(row, col):
            raise ValueError(
                f"Cell ({row},{col}) is out of bounds for a "
                f"{self._rows}×{self._cols} grid."
            )

    def __repr__(self) -> str:
        return (
            f"GridMap(rows={self._rows}, cols={self._cols}, "
            f"obstacles={self.obstacle_count})"
        )

    def to_ascii(self) -> str:
        """
        Render a small ASCII representation for debugging.
        '.' = free, '#' = obstacle.
        Only recommended for small grids (≤ 20×20).
        """
        lines = []
        for r in range(self._rows):
            row_chars = []
            for c in range(self._cols):
                row_chars.append("#" if self.is_obstacle(r, c) else ".")
            lines.append("".join(row_chars))
        return "\n".join(lines)
