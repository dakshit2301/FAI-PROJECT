"""
benchmark/scenarios.py
----------------------
Predefined benchmark scenario definitions.

A BenchmarkScenario fully specifies one experimental condition.
The BenchmarkRunner uses these to generate reproducible maps,
sample start/goal pairs, and run all three algorithms.

Scenario taxonomy
~~~~~~~~~~~~~~~~~
Grid scenarios vary size and obstacle density independently so we can
observe how each factor affects algorithm behaviour.

Campus scenarios run the same CampusGraph algorithms against the named
campus map, which is fixed in structure (no random obstacles).

All seeds are fixed constants so results are reproducible across machines
and Python versions (random.Random, not numpy.random).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

MapMode = Literal["grid", "campus"]


@dataclass(frozen=True)
class BenchmarkScenario:
    """
    Fully specifies one benchmark experimental condition.

    Parameters
    ----------
    name : str
        Human-readable label used in charts and CSV output.
    map_mode : "grid" | "campus"
        "grid"   → generate a GridMap with random obstacles.
        "campus" → use the default CampusGraph (fixed topology).
    rows, cols : int
        Grid dimensions.  Ignored when map_mode="campus".
    obstacle_density : float
        Fraction of grid cells that are obstacles (0.0–0.9).
        Ignored when map_mode="campus".
    seed : int
        Random seed for map generation AND start/goal sampling.
        Same seed → identical maps and pairs on every run.
    num_trials : int
        Number of independent (start, goal) pairs to average over.
    description : str
        One-line description shown in the methodology section.
    """

    name: str
    map_mode: MapMode = "grid"
    rows: int = 10
    cols: int = 10
    obstacle_density: float = 0.0
    seed: int = 42
    num_trials: int = 5
    description: str = ""

    def __post_init__(self) -> None:
        if self.map_mode not in ("grid", "campus"):
            raise ValueError(f"Unsupported map_mode: {self.map_mode!r}.")
        if self.num_trials < 1:
            raise ValueError("num_trials must be at least 1.")
        if self.map_mode == "grid":
            if self.rows < 1 or self.cols < 1:
                raise ValueError("Grid rows and columns must be at least 1.")
            if not math.isfinite(self.obstacle_density) or not (
                0.0 <= self.obstacle_density <= 0.9
            ):
                raise ValueError(
                    "Grid obstacle_density must be finite and in [0.0, 0.9]."
                )

    @property
    def grid_size(self) -> int:
        return self.rows * self.cols

    @property
    def label(self) -> str:
        """Short label for chart axes."""
        if self.map_mode == "campus":
            return f"Campus"
        return f"{self.name}\n({self.rows}×{self.cols}, {int(self.obstacle_density*100)}%)"


# ---------------------------------------------------------------------------
# Standard scenario catalogue
# ---------------------------------------------------------------------------

SCENARIOS: list[BenchmarkScenario] = [
    BenchmarkScenario(
        name="Tiny-Open",
        map_mode="grid",
        rows=5, cols=5,
        obstacle_density=0.0,
        seed=1,
        num_trials=5,
        description="5×5 obstacle-free grid. Smoke test; trivially verifiable by hand.",
    ),
    BenchmarkScenario(
        name="Small-Light",
        map_mode="grid",
        rows=10, cols=10,
        obstacle_density=0.10,
        seed=2,
        num_trials=5,
        description="10×10 grid with 10% obstacles. Light obstruction.",
    ),
    BenchmarkScenario(
        name="Medium-Moderate",
        map_mode="grid",
        rows=20, cols=20,
        obstacle_density=0.20,
        seed=3,
        num_trials=5,
        description="20×20 grid with 20% obstacles. Moderate challenge.",
    ),
    BenchmarkScenario(
        name="Large-Dense",
        map_mode="grid",
        rows=30, cols=30,
        obstacle_density=0.30,
        seed=4,
        num_trials=5,
        description="30×30 grid with 30% obstacles. Dense obstacles, harder paths.",
    ),
    BenchmarkScenario(
        name="Stress-Test",
        map_mode="grid",
        rows=50, cols=50,
        obstacle_density=0.15,
        seed=5,
        num_trials=3,
        description="50×50 grid with 15% obstacles. Performance stress test.",
    ),
    BenchmarkScenario(
        name="Campus-Graph",
        map_mode="campus",
        seed=10,
        num_trials=5,
        description="Default 20-node campus graph. Fixed weighted topology.",
    ),
]

# Quick subset for fast unit tests (avoids running the full benchmark in CI)
FAST_SCENARIOS: list[BenchmarkScenario] = [
    BenchmarkScenario(
        name="Tiny-Open",
        map_mode="grid",
        rows=5, cols=5,
        obstacle_density=0.0,
        seed=1,
        num_trials=3,
        description="Fast smoke-test scenario.",
    ),
    BenchmarkScenario(
        name="Small-Light",
        map_mode="grid",
        rows=10, cols=10,
        obstacle_density=0.10,
        seed=2,
        num_trials=3,
        description="Fast small scenario.",
    ),
    BenchmarkScenario(
        name="Campus-Graph",
        map_mode="campus",
        seed=10,
        num_trials=3,
        description="Fast campus scenario.",
    ),
]
