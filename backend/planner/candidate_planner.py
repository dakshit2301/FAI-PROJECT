"""
planner/candidate_planner.py
-----------------------------
Multi-candidate search orchestration.

Problem statement
~~~~~~~~~~~~~~~~~
The user does not know *which* candidate location holds the item.
They supply a list of candidate locations and (optionally) a probability
belief for each.  The planner must:

1. Run the chosen search algorithm independently from the current position
   to each candidate location.
2. Score each candidate using a priority formula that balances:
       - pathfinding cost   (how far away the location is)
       - search cost        (how hard the location is to search once reached)
       - probability belief (how likely the item is there)
3. Return the candidates sorted by priority score (ascending = search first).
4. Provide a recommended visit order using a greedy nearest-neighbor tour
   approximation.

Definitions (stable — do not change in UI code)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Term                Definition
────────────────────────────────────────────────────────────────────────────
pathfinding_cost    Sum of edge weights from current_position to candidate.
                    Computed by the chosen search algorithm.
search_cost         User-assigned effort to physically search that location
                    (stored in Node.search_cost, scale 1.0–5.0).
total_cost          pathfinding_cost + search_cost
probability_weight  User-supplied belief that item is there (0.0 – 1.0).
                    Default 0.5 when not specified.
priority_score      total_cost × (1 − probability_weight)
                    Lower → search this candidate sooner.
────────────────────────────────────────────────────────────────────────────

What we do NOT claim
~~~~~~~~~~~~~~~~~~~~
* Probabilities are NOT learned from data — they are user-supplied beliefs.
* The visit order is a greedy nearest-neighbor approximation, NOT an optimal
  TSP solution.  The TSP is NP-hard; documenting this is mandatory.
* A* being used here for pathfinding does NOT make the multi-candidate
  ordering "AI-learned".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Union

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.models import SearchResult
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import (
    euclidean_distance,
    manhattan_distance,
    null_heuristic,
)

MapType = Union[CampusGraph, GridMap]
AlgorithmName = Literal["bfs", "greedy", "astar"]

# Default probability belief when user provides none
DEFAULT_PROBABILITY: float = 0.5


# ---------------------------------------------------------------------------
# CandidateResult — result for one candidate location
# ---------------------------------------------------------------------------

@dataclass
class CandidateResult:
    """
    Full result for a single candidate location.

    Attributes
    ----------
    candidate : str
        Name of the candidate location.
    pathfinding_cost : float
        Cost to travel from current position to this candidate
        (sum of edge weights; 0.0 if unreachable or start==candidate).
    search_cost : float
        Effort to physically search the candidate location (1.0–5.0).
        Taken from Node.search_cost if available, else 1.0.
    total_cost : float
        pathfinding_cost + search_cost
    probability_weight : float
        User-supplied belief that item is here (0.0–1.0).
    priority_score : float
        total_cost × (1 − probability_weight).
        Lower score → this candidate should be searched first.
    algorithm_result : SearchResult
        The full pathfinding result from start → this candidate.
    rank : int
        Position in the sorted visit order (1 = search first).
        Set to 0 until ``CandidatePlanner.plan()`` assigns ranks.
    """

    candidate: str
    pathfinding_cost: float
    search_cost: float
    total_cost: float
    probability_weight: float
    priority_score: float
    algorithm_result: SearchResult
    rank: int = 0

    @property
    def reachable(self) -> bool:
        return self.algorithm_result.success

    @property
    def path(self) -> list[str]:
        return self.algorithm_result.path

    def summary_dict(self) -> dict:
        """Flat dict for pandas / CSV export."""
        return {
            "rank": self.rank,
            "candidate": self.candidate,
            "reachable": self.reachable,
            "pathfinding_cost": self.pathfinding_cost,
            "search_cost": self.search_cost,
            "total_cost": self.total_cost,
            "probability_weight": self.probability_weight,
            "priority_score": self.priority_score,
            "path_length": self.algorithm_result.path_length,
            "nodes_expanded": self.algorithm_result.nodes_expanded,
            "execution_time_ms": self.algorithm_result.execution_time_ms,
        }


@dataclass(frozen=True)
class MissionStep:
    """One route and location inspection in a simulated recovery mission."""

    from_location: str
    candidate: str
    algorithm_result: SearchResult
    item_found: bool


# ---------------------------------------------------------------------------
# CandidatePlanner
# ---------------------------------------------------------------------------

class CandidatePlanner:
    """
    Plans a multi-candidate search from a single starting position.

    Parameters
    ----------
    graph : CampusGraph | GridMap
        The environment to search.
    algorithm : "bfs" | "greedy" | "astar"
        Which pathfinding algorithm to use for each candidate.
    heuristic : callable, optional
        Heuristic function required by Greedy and A*.
        Ignored for BFS.
        If None, a default is chosen based on graph type:
          CampusGraph → euclidean_distance
          GridMap     → manhattan_distance
    """

    def __init__(
        self,
        graph: MapType,
        algorithm: AlgorithmName = "astar",
        heuristic: Optional[Callable] = None,
    ) -> None:
        if algorithm not in ("bfs", "greedy", "astar"):
            raise ValueError(f"Unsupported search algorithm: {algorithm!r}.")
        self._graph = graph
        self._algorithm = algorithm
        self._heuristic = heuristic or self._default_heuristic(graph)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(
        self,
        start: str,
        candidates: list[str],
        probabilities: Optional[dict[str, float]] = None,
    ) -> list[CandidateResult]:
        """
        Run pathfinding from *start* to every candidate and rank them.

        Parameters
        ----------
        start : str
            Current / last-known position.
        candidates : list[str]
            Location names to consider.  May include duplicates or invalid
            names — duplicates are deduplicated, invalid names produce a
            failed CandidateResult.
        probabilities : dict[str, float], optional
            Mapping of candidate_name → probability belief (0.0–1.0).
            Missing candidates default to ``DEFAULT_PROBABILITY`` (0.5).
            Values are clamped to [0.0, 1.0].

        Returns
        -------
        list[CandidateResult]
            Sorted by priority_score ascending (search first = index 0).
            Unreachable candidates are included at the end, sorted by name.

        Notes
        -----
        * Each candidate's pathfinding sub-problem is independent.
        * Unreachable candidates are included with ``reachable=False`` and
          a priority_score of ``math.inf`` so they sort to the bottom.
        """
        if not candidates:
            return []

        probs = probabilities or {}
        seen: set[str] = set()
        results: list[CandidateResult] = []

        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)

            prob = probs.get(cand, DEFAULT_PROBABILITY)
            if not math.isfinite(prob):
                raise ValueError(
                    f"Probability for '{cand}' must be finite, got {prob!r}."
                )
            prob = max(0.0, min(1.0, prob))
            cr = self._evaluate_candidate(start, cand, prob)
            results.append(cr)

        # Sort: reachable first by priority_score, unreachable last by name
        reachable = sorted(
            [r for r in results if r.reachable],
            key=lambda r: r.priority_score,
        )
        unreachable = sorted(
            [r for r in results if not r.reachable],
            key=lambda r: r.candidate,
        )

        ordered = reachable + unreachable
        for i, cr in enumerate(ordered, start=1):
            cr.rank = i

        return ordered

    def recommended_visit_order(
        self,
        results: list[CandidateResult],
        start: Optional[str] = None,
    ) -> list[str]:
        """
        Compute a greedy nearest-neighbor visit order over reachable candidates.

        This is a well-known O(n^2) approximation for the Travelling Salesman
        Problem (TSP). It is NOT optimal (optimal TSP is NP-hard).

        Parameters
        ----------
        results : list[CandidateResult]
            Output of ``plan()``. Unreachable entries are excluded.
        start : str, optional
            Starting location name. If None, starts from the candidate with
            the lowest priority_score.

        Returns
        -------
        list[str]
            Ordered candidate names in nearest-neighbor visit sequence.
        """
        reachable = [r for r in results if r.reachable]
        if not reachable:
            return []

        if len(reachable) == 1:
            return [reachable[0].candidate]

        # Remaining candidates to visit
        remaining = [r.candidate for r in reachable]

        # Determine tour starting point
        current = start if (start and (
            (isinstance(self._graph, CampusGraph) and self._graph.has_node(start))
            or (isinstance(self._graph, GridMap) and self._is_valid_grid_node(start))
        )) else reachable[0].candidate

        order: list[str] = []

        # If current is in remaining and is not the external starting location, visit it
        if current in remaining and current != start:
            order.append(current)
            remaining.remove(current)

        while remaining:
            # Find closest unvisited candidate from current position
            best_cand = None
            best_dist = math.inf

            for cand in remaining:
                res = self._run_search(current, cand)
                dist = res.path_cost if res.success else math.inf
                if dist < best_dist:
                    best_dist = dist
                    best_cand = cand

            if best_cand is None or math.isinf(best_dist):
                best_cand = remaining[0]

            order.append(best_cand)
            remaining.remove(best_cand)
            current = best_cand

        return order

    def execute_mission(
        self,
        start: str,
        visit_order: list[str],
        actual_location: str,
    ) -> list[MissionStep]:
        """
        Simulate searching candidates in order, replanning from each room
        after an unsuccessful inspection.

        The selected actual location acts as the simulation's item sensor:
        it is reported as recovered only when that candidate is reached.
        """
        steps: list[MissionStep] = []
        current = start

        for candidate in visit_order:
            result = self._run_search(current, candidate)
            found = result.success and candidate == actual_location
            steps.append(
                MissionStep(
                    from_location=current,
                    candidate=candidate,
                    algorithm_result=result,
                    item_found=found,
                )
            )
            if found:
                break
            if result.success:
                current = candidate

        return steps

    def _is_valid_grid_node(self, name: str) -> bool:
        """Check if name is an in-bounds grid cell."""
        try:
            r, c = GridMap.name_to_pos(name)
            return self._graph.is_valid(r, c)
        except (ValueError, AttributeError):
            return False

    def algorithm_name(self) -> str:
        """Human-readable algorithm name."""
        return {"bfs": "BFS", "greedy": "Greedy", "astar": "A*"}.get(
            self._algorithm, self._algorithm.upper()
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_candidate(
        self, start: str, candidate: str, prob: float
    ) -> CandidateResult:
        """Run pathfinding from start → candidate and build CandidateResult."""
        result = self._run_search(start, candidate)

        if result.success:
            pathfinding_cost = result.path_cost
        else:
            pathfinding_cost = math.inf

        search_cost = self._get_search_cost(candidate)

        if math.isinf(pathfinding_cost):
            total_cost = math.inf
            priority_score = math.inf
        else:
            total_cost = pathfinding_cost + search_cost
            priority_score = total_cost * (1.0 - prob)

        return CandidateResult(
            candidate=candidate,
            pathfinding_cost=pathfinding_cost,
            search_cost=search_cost,
            total_cost=total_cost,
            probability_weight=prob,
            priority_score=priority_score,
            algorithm_result=result,
        )

    def _run_search(self, start: str, goal: str) -> SearchResult:
        """Dispatch to the selected algorithm."""
        if self._algorithm == "bfs":
            return bfs(self._graph, start, goal)
        elif self._algorithm == "greedy":
            return greedy_best_first(self._graph, start, goal, self._heuristic)
        else:  # astar (default)
            return astar(self._graph, start, goal, self._heuristic)

    def _get_search_cost(self, candidate: str) -> float:
        """
        Return the search cost for a candidate location.

        For CampusGraph nodes, use Node.search_cost.
        For GridMap cells, default to 1.0 (uniform).
        For unknown / invalid names, default to 1.0.
        """
        if isinstance(self._graph, CampusGraph):
            try:
                return self._graph.get_node(candidate).search_cost
            except KeyError:
                return 1.0
        return 1.0  # GridMap has no per-cell search cost

    @staticmethod
    def _default_heuristic(graph: MapType) -> Callable:
        """Choose the most appropriate heuristic for this graph type."""
        if isinstance(graph, CampusGraph):
            return euclidean_distance
        return manhattan_distance
