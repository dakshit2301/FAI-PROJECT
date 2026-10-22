"""Reproducible evidence helpers for the final AI project submission."""

from __future__ import annotations

import pandas as pd

from environment.locations import build_default_campus, location_names
from planner.candidate_planner import CandidatePlanner, MissionStep


def build_decision_log(
    start: str,
    algorithm: str,
    steps: list[MissionStep],
) -> str:
    """Create a concise, auditable step-by-step log for one simulated mission."""
    lines = [
        "# Lost Item Recovery Demonstration Log",
        "",
        f"- Start location: {start}",
        f"- Pathfinding algorithm: {algorithm}",
        "",
        "| Step | From | Inspect | Route | Cost | Expanded | Outcome |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for index, step in enumerate(steps, start=1):
        result = step.algorithm_result
        route = " -> ".join(result.path) if result.success else "No route"
        outcome = "Item recovered" if step.item_found else (
            "Unreachable" if not result.success else "Not found; replan"
        )
        lines.append(
            f"| {index} | {step.from_location} | {step.candidate} | {route} | "
            f"{result.path_cost:.2f} | {result.nodes_expanded} | {outcome} |"
        )
    return "\n".join(lines) + "\n"


def candidate_count_sensitivity(
    counts: tuple[int, ...] = (1, 2, 3, 4, 5),
    start: str = "Main Entrance",
) -> pd.DataFrame:
    """Measure planning work as the candidate set grows on the fixed campus map.

    The ordered locations are deterministic. Each algorithm receives exactly the
    same prefix at each count, making the comparison repeatable and fair.
    """
    available = [name for name in location_names() if name != start]
    rows: list[dict] = []
    for count in counts:
        if count < 1 or count > len(available):
            raise ValueError("candidate counts must fit the bundled campus map")
        candidates = available[:count]
        probabilities = {name: 0.5 for name in candidates}
        for algorithm in ("bfs", "greedy", "astar"):
            plan = CandidatePlanner(build_default_campus(), algorithm=algorithm).plan(
                start, candidates, probabilities
            )
            rows.append({
                "candidate_count": count,
                "algorithm": {"bfs": "BFS", "greedy": "Greedy", "astar": "A*"}[algorithm],
                "total_nodes_expanded": sum(item.algorithm_result.nodes_expanded for item in plan),
                "total_execution_time_ms": sum(item.algorithm_result.execution_time_ms for item in plan),
                "reachable_candidates": sum(item.reachable for item in plan),
            })
    return pd.DataFrame(rows)
