"""
benchmark/runner.py
-------------------
BenchmarkRunner — runs all three algorithms on every scenario and collects
raw metrics into a pandas DataFrame.

Metric definitions (stable)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Metric               Unit      Definition
────────────────────────────────────────────────────────────────────────────
execution_time_ms    ms        Real wall-clock time around algorithm core
                               only (time.perf_counter).  Excludes I/O and
                               Streamlit rendering.
nodes_expanded       count     Nodes popped from the frontier (main loop
                               iterations; a reopened A* state counts again).
nodes_generated      count     Nodes pushed to the frontier (neighbours
                               enqueued, duplicates included).
path_cost            units     Sum of edge weights along the returned path.
                               For uniform grids = path_length (hop count).
path_length          hops      Number of edges in the returned path
                               (len(path) - 1).  0 if start == goal.
success              bool      True if a path to the goal was found.
────────────────────────────────────────────────────────────────────────────

The "movement distance" in the requirements maps to path_cost.  On a grid
with uniform edge weight 1.0, path_cost == path_length == movement distance.
On the weighted campus graph, path_cost (sum of weights) is the movement
cost while path_length is the number of rooms traversed.

Fairness rules (enforced in code)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. All three algorithms use the same GridMap / CampusGraph instance per trial.
2. Start and goal are sampled using the same RNG and the same seed per scenario.
3. Each algorithm measures its own wall time, including input validation and
   path reconstruction, but excluding UI rendering and benchmark setup.
4. Results are never hard-coded. If a run fails, path metrics are NaN while
   measured search effort and runtime are retained.
5. Trials where start == goal are skipped (trivial, not informative).
"""

from __future__ import annotations

import random
import tracemalloc
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from benchmark.scenarios import BenchmarkScenario, SCENARIOS
from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import build_default_campus
from environment.models import SearchResult
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import euclidean_distance, manhattan_distance


# ---------------------------------------------------------------------------
# BenchmarkRecord — one row in the output DataFrame
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkRecord:
    """
    One algorithm run on one (start, goal) trial.

    Path cost and path length are NaN when success=False. Search effort
    and runtime remain measured for failed runs.
    """

    scenario_name: str
    map_mode: str               # "grid" or "campus"
    grid_size: int              # rows × cols (0 for campus)
    obstacle_density: float     # 0.0 for campus
    algorithm: str              # "BFS" | "Greedy" | "A*"
    trial: int                  # 1-indexed trial number
    start: str
    goal: str
    success: bool
    path_cost: float            # NaN if not success
    path_length: int            # NaN (stored as float) if not success
    nodes_expanded: int
    nodes_generated: int
    execution_time_ms: float
    memory_peak_kib: float
    heuristic_used: str         # "none" for BFS

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "map_mode": self.map_mode,
            "grid_size": self.grid_size,
            "obstacle_density": self.obstacle_density,
            "algorithm": self.algorithm,
            "trial": self.trial,
            "start": self.start,
            "goal": self.goal,
            "success": self.success,
            "path_cost": self.path_cost,
            "path_length": self.path_length,
            "nodes_expanded": self.nodes_expanded,
            "nodes_generated": self.nodes_generated,
            "execution_time_ms": self.execution_time_ms,
            "memory_peak_kib": self.memory_peak_kib,
            "heuristic_used": self.heuristic_used,
        }


# ---------------------------------------------------------------------------
# BenchmarkRunner
# ---------------------------------------------------------------------------

class BenchmarkRunner:
    """
    Runs all three search algorithms on benchmark scenarios and collects results.

    Parameters
    ----------
    verbose : bool
        Print progress to stdout during a run (useful for long benchmarks).
    """

    ALGORITHMS: list[str] = ["BFS", "Greedy", "A*"]

    def __init__(
        self,
        scenarios: Optional[list[BenchmarkScenario]] = None,
        verbose: bool = False,
    ) -> None:
        if isinstance(scenarios, bool):
            self._scenarios = None
            self._verbose = scenarios
        else:
            self._scenarios = scenarios
            self._verbose = verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_scenario(self, scenario: BenchmarkScenario) -> list[BenchmarkRecord]:
        """
        Run all three algorithms across all trials for one scenario.

        Returns
        -------
        list[BenchmarkRecord]
            One record per (algorithm × trial) combination.
        """
        if scenario.map_mode == "campus":
            return self._run_campus_scenario(scenario)
        return self._run_grid_scenario(scenario)

    def run_all(
        self,
        scenarios: Optional[list[BenchmarkScenario]] = None,
    ) -> pd.DataFrame:
        """
        Run all scenarios and return a tidy pandas DataFrame.

        Parameters
        ----------
        scenarios : list[BenchmarkScenario], optional
            Defaults to the initialized scenarios or standard SCENARIOS catalogue.

        Returns
        -------
        pd.DataFrame
            One row per (scenario × algorithm × trial).
            Columns match BenchmarkRecord.to_dict() keys.
        """
        if scenarios is None:
            scenarios = self._scenarios if self._scenarios is not None else SCENARIOS

        all_records: list[BenchmarkRecord] = []
        for i, scenario in enumerate(scenarios, 1):
            if self._verbose:
                print(f"[{i}/{len(scenarios)}] Running scenario: {scenario.name}")
            records = self.run_scenario(scenario)
            all_records.extend(records)

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame([r.to_dict() for r in all_records])
        return df

    # ------------------------------------------------------------------
    # Grid scenario
    # ------------------------------------------------------------------

    def _run_grid_scenario(self, scenario: BenchmarkScenario) -> list[BenchmarkRecord]:
        """
        Build the grid once, then run each trial with fresh start/goal pairs.
        All three algorithms see the SAME grid instance per trial.
        """
        grid = GridMap.from_obstacle_density(
            scenario.rows,
            scenario.cols,
            scenario.obstacle_density,
            seed=scenario.seed,
        )
        heuristic = manhattan_distance

        # Sample start/goal pairs using a separate RNG (seed derived from scenario seed)
        pairs = self._sample_grid_pairs(grid, scenario.num_trials, scenario.seed)
        records: list[BenchmarkRecord] = []

        for trial_idx, (start, goal) in enumerate(pairs, start=1):
            for algo_name in self.ALGORITHMS:
                result, memory_peak_kib = self._run_profiled_algorithm(
                    algo_name, grid, start, goal, heuristic
                )
                record = self._make_record(
                    scenario, algo_name, trial_idx, start, goal, result, memory_peak_kib
                )
                records.append(record)

        return records

    # ------------------------------------------------------------------
    # Campus scenario
    # ------------------------------------------------------------------

    def _run_campus_scenario(self, scenario: BenchmarkScenario) -> list[BenchmarkRecord]:
        """
        Build a fresh campus graph and sample named location pairs.
        """
        campus = build_default_campus()
        node_names = campus.node_names()
        heuristic = euclidean_distance

        pairs = self._sample_campus_pairs(node_names, scenario.num_trials, scenario.seed)
        records: list[BenchmarkRecord] = []

        for trial_idx, (start, goal) in enumerate(pairs, start=1):
            for algo_name in self.ALGORITHMS:
                result, memory_peak_kib = self._run_profiled_algorithm(
                    algo_name, campus, start, goal, heuristic
                )
                record = self._make_record(
                    scenario, algo_name, trial_idx, start, goal, result, memory_peak_kib
                )
                records.append(record)

        return records

    # ------------------------------------------------------------------
    # Algorithm dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _run_algorithm(
        algo_name: str,
        graph,
        start: str,
        goal: str,
        heuristic,
    ) -> SearchResult:
        """
        Call the correct algorithm function.
        timing is captured inside each algorithm via time.perf_counter().
        """
        if algo_name == "BFS":
            return bfs(graph, start, goal)
        elif algo_name == "Greedy":
            return greedy_best_first(graph, start, goal, heuristic)
        else:  # A*
            return astar(graph, start, goal, heuristic)

    @classmethod
    def _run_profiled_algorithm(cls, algo_name, graph, start, goal, heuristic):
        """Run one search and record its Python allocation peak in KiB.

        ``execution_time_ms`` remains the algorithm's own wall-clock timing;
        memory profiling is deliberately recorded separately so the benchmark
        does not confuse instrumentation cost with search time.
        """
        tracemalloc.start()
        try:
            result = cls._run_algorithm(algo_name, graph, start, goal, heuristic)
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return result, peak_bytes / 1024.0

    # ------------------------------------------------------------------
    # Record construction
    # ------------------------------------------------------------------

    @staticmethod
    def _make_record(
        scenario: BenchmarkScenario,
        algo_name: str,
        trial: int,
        start: str,
        goal: str,
        result: SearchResult,
        memory_peak_kib: float,
    ) -> BenchmarkRecord:
        nan = float("nan")
        return BenchmarkRecord(
            scenario_name=scenario.name,
            map_mode=scenario.map_mode,
            grid_size=scenario.grid_size if scenario.map_mode == "grid" else 0,
            obstacle_density=scenario.obstacle_density if scenario.map_mode == "grid" else 0.0,
            algorithm=algo_name,
            trial=trial,
            start=start,
            goal=goal,
            success=result.success,
            path_cost=result.path_cost if result.success else nan,
            path_length=result.path_length if result.success else nan,
            nodes_expanded=result.nodes_expanded,
            nodes_generated=result.nodes_generated,
            execution_time_ms=result.execution_time_ms,
            memory_peak_kib=memory_peak_kib,
            heuristic_used=result.heuristic_used or "none",
        )

    # ------------------------------------------------------------------
    # Pair sampling helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_grid_pairs(
        grid: GridMap,
        num_trials: int,
        seed: int,
    ) -> list[tuple[str, str]]:
        """
        Sample (start, goal) pairs from non-obstacle grid cells.

        Rules:
        - Pairs are reproducible (same seed → same pairs).
        - start != goal (trivial case excluded).
        - Both cells must be walkable (not obstacles).
        """
        rng = random.Random(seed + 1000)  # offset from map-gen seed
        valid_cells = list(grid.all_names())
        if len(valid_cells) < 2:
            return []

        pairs: list[tuple[str, str]] = []
        attempts = 0
        while len(pairs) < num_trials and attempts < num_trials * 100:
            attempts += 1
            start = rng.choice(valid_cells)
            goal = rng.choice(valid_cells)
            if start != goal:
                pairs.append((start, goal))

        return pairs

    @staticmethod
    def _sample_campus_pairs(
        node_names: list[str],
        num_trials: int,
        seed: int,
    ) -> list[tuple[str, str]]:
        """Sample (start, goal) pairs from campus node names."""
        rng = random.Random(seed + 2000)
        if len(node_names) < 2:
            return []

        pairs: list[tuple[str, str]] = []
        attempts = 0
        while len(pairs) < num_trials and attempts < num_trials * 100:
            attempts += 1
            start = rng.choice(node_names)
            goal = rng.choice(node_names)
            if start != goal:
                pairs.append((start, goal))

        return pairs
