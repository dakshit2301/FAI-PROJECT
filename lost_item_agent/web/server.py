"""Local Flask API and static website for the Lost Item Recovery Agent."""

from __future__ import annotations

import math
import multiprocessing
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from ipaddress import ip_address

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException, abort

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from environment.graph import CampusGraph
from environment.grid import GridMap
from environment.locations import (
    ITEM_TYPE_CANDIDATES,
    build_default_campus,
    location_names,
)
from search.astar import astar
from search.bfs import bfs
from search.greedy import greedy_best_first
from search.heuristics import euclidean_distance, manhattan_distance, null_heuristic
from planner.candidate_planner import CandidatePlanner, CandidateResult, MissionStep

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
BENCHMARK_TIMEOUT_SECONDS = 30

MAP_LAYOUT: dict[str, tuple[float, float, str]] = {
    "Main Entrance": (1.0, 1.0, "Ground floor"),
    "Reception": (3.0, 1.0, "Ground floor"),
    "Canteen": (5.0, 1.0, "Ground floor"),
    "Washroom-G": (7.0, 1.0, "Ground floor"),
    "Corridor-G1": (1.0, 2.5, "Ground floor"),
    "Corridor-G2": (3.0, 2.5, "Ground floor"),
    "Corridor-G3": (5.0, 2.5, "Ground floor"),
    "Library": (1.0, 4.0, "Ground floor"),
    "Lab-A": (3.0, 4.0, "Ground floor"),
    "Lab-B": (5.0, 4.0, "Ground floor"),
    "Parking": (7.0, 2.5, "Ground floor"),
    "Stairwell": (2.0, 5.5, "Connector"),
    "Corridor-F1": (4.0, 5.5, "First floor"),
    "Corridor-F2": (6.0, 5.5, "First floor"),
    "Classroom-101": (2.0, 7.0, "First floor"),
    "Classroom-102": (4.0, 7.0, "First floor"),
    "Classroom-103": (6.0, 7.0, "First floor"),
    "Office-A": (2.0, 8.5, "First floor"),
    "Office-B": (4.0, 8.5, "First floor"),
    "Washroom-F": (6.0, 8.5, "First floor"),
}

ALGORITHMS = {"bfs", "greedy", "astar"}
HEURISTICS = {
    "euclidean": euclidean_distance,
    "manhattan": manhattan_distance,
    "none": null_heuristic,
}


def _run_benchmark_worker(scenarios: list[Any], sender: Any) -> None:
    """Run benchmark and serialize its results in an isolated child process."""
    try:
        from benchmark.exporter import summarize
        from benchmark.runner import BenchmarkRunner

        raw = BenchmarkRunner(verbose=False).run_all(scenarios)
        summary = summarize(raw)
        sender.send({
            "scenarios": [scenario.name for scenario in scenarios],
            "summary": summary.astype(object).where(summary.notna(), None).to_dict("records"),
            "raw_csv": raw.to_csv(index=False),
            "summary_csv": summary.to_csv(index=False),
        })
    except Exception as error:
        sender.send({"error": str(error)})
    finally:
        sender.close()


def _run_benchmarks_with_timeout(scenarios: list[Any]) -> dict[str, Any]:
    """Run benchmarks in a killable process, enforcing a hard wall-clock limit."""
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_run_benchmark_worker,
        args=(scenarios, sender),
        daemon=True,
    )
    deadline = time.monotonic() + BENCHMARK_TIMEOUT_SECONDS
    process.start()
    sender.close()

    result = None
    try:
        while process.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if receiver.poll(min(remaining, 0.05)):
                result = receiver.recv()
                break

        if result is None and receiver.poll():
            result = receiver.recv()

        if result is None and process.is_alive():
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
            raise TimeoutError(
                f"Benchmark exceeded the {BENCHMARK_TIMEOUT_SECONDS}-second time limit."
            )

        process.join(timeout=max(0, deadline - time.monotonic()))
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
            raise TimeoutError(
                f"Benchmark exceeded the {BENCHMARK_TIMEOUT_SECONDS}-second time limit."
            )
        if result is None:
            raise RuntimeError("Benchmark worker exited without returning a result.")
        if process.exitcode != 0 and "error" not in result:
            raise RuntimeError(
                f"Benchmark worker exited unexpectedly (code {process.exitcode})."
            )
        if "error" in result:
            raise RuntimeError(f"Benchmark failed: {result['error']}")
        return result
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()


def _required_text(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{name}' must be a non-empty string.")
    return value.strip()


def _text_list(data: dict[str, Any], name: str) -> list[str]:
    value = data.get(name, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"'{name}' must be a list of strings.")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def _search_configuration(data: dict[str, Any]) -> tuple[str, Any]:
    algorithm = data.get("algorithm", "astar")
    heuristic_name = data.get("heuristic", "euclidean")
    if not isinstance(algorithm, str) or algorithm not in ALGORITHMS:
        raise ValueError("'algorithm' must be one of bfs, greedy, or astar.")
    if not isinstance(heuristic_name, str) or heuristic_name not in HEURISTICS:
        raise ValueError("'heuristic' must be euclidean, manhattan, or none.")
    return algorithm, HEURISTICS[heuristic_name]


def _campus_with_blocks(blocked_edges: list[Any]) -> tuple[CampusGraph, list[list[str]]]:
    if not isinstance(blocked_edges, list):
        raise ValueError("'blocked_edges' must be a list.")
    graph = build_default_campus()
    valid_edges: list[list[str]] = []
    for edge in blocked_edges:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or any(not isinstance(name, str) for name in edge)
        ):
            raise ValueError("Each blocked edge must be a pair of location names.")
        source, target = edge
        if not graph.has_edge(source, target):
            raise ValueError(f"No campus corridor connects '{source}' and '{target}'.")
        graph.block_edge(source, target)
        valid_edges.append([source, target])
    return graph, valid_edges


def _finite(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _search_result(result: Any) -> dict[str, Any]:
    return {
        "algorithm": result.algorithm,
        "start": result.start,
        "goal": result.goal,
        "success": result.success,
        "path": result.path,
        "path_length": result.path_length,
        "path_cost": _finite(result.path_cost),
        "nodes_expanded": result.nodes_expanded,
        "nodes_generated": result.nodes_generated,
        "execution_time_ms": result.execution_time_ms,
        "heuristic_used": result.heuristic_used,
        "explored_nodes": result.explored_nodes,
        "notes": result.notes,
    }


def _candidate_result(result: CandidateResult) -> dict[str, Any]:
    return {
        "rank": result.rank,
        "candidate": result.candidate,
        "reachable": result.reachable,
        "pathfinding_cost": _finite(result.pathfinding_cost),
        "search_cost": result.search_cost,
        "total_cost": _finite(result.total_cost),
        "probability_weight": result.probability_weight,
        "priority_score": _finite(result.priority_score),
        "path_length": result.algorithm_result.path_length,
        "nodes_expanded": result.algorithm_result.nodes_expanded,
        "execution_time_ms": result.algorithm_result.execution_time_ms,
        "path": result.path,
    }


def _mission_step(step: MissionStep, item_description: str) -> dict[str, Any]:
    return {
        "from_location": step.from_location,
        "candidate": step.candidate,
        "found": step.item_found,
        "status": (
            f"{item_description} recovered"
            if step.item_found
            else "Not found"
            if step.algorithm_result.success
            else "Location unreachable"
        ),
        "search": _search_result(step.algorithm_result),
    }


def _validate_probabilities(raw: Any, candidates: list[str]) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("'probabilities' must be an object.")
    probabilities: dict[str, float] = {}
    for candidate in candidates:
        value = raw.get(candidate, 0.5)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Belief for '{candidate}' must be a number from 0 to 1.")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"Belief for '{candidate}' must be between 0 and 1.")
        probabilities[candidate] = float(value)
    return probabilities


@app.errorhandler(ValueError)
def handle_value_error(error: ValueError):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(HTTPException)
def handle_http_exception(error: HTTPException):
    if request.path.startswith("/api/"):
        return jsonify({
            "error": error.description,
            "status": error.code,
        }), error.code
    return error


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/api/config")
def get_config():
    campus = build_default_campus()
    nodes = []
    for node in campus.all_nodes():
        x, y, floor = MAP_LAYOUT[node.name]
        nodes.append({
            "name": node.name,
            "type": node.node_type,
            "search_cost": node.search_cost,
            "x": x,
            "y": y,
            "floor": floor,
        })
    edges = [
        {
            "source": edge.source,
            "target": edge.target,
            "weight": edge.weight,
        }
        for edge in campus.all_edges()
    ]
    return jsonify({
        "locations": location_names(),
        "item_candidates": ITEM_TYPE_CANDIDATES,
        "nodes": nodes,
        "edges": edges,
        "algorithms": ["bfs", "greedy", "astar"],
        "heuristics": ["euclidean", "manhattan", "none"],
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/search/campus")
def search_campus():
    data = request.get_json(silent=False)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    start = _required_text(data, "start")
    last_seen = _required_text(data, "last_seen")
    candidates = _text_list(data, "candidates")
    visited = _text_list(data, "visited")
    candidates = list(dict.fromkeys([*candidates, *visited]))
    if not candidates:
        raise ValueError("Select at least one likely or visited location.")
    if any(candidate not in location_names() for candidate in candidates):
        raise ValueError("All candidates must be known campus locations.")
    if start not in location_names() or last_seen not in location_names():
        raise ValueError("Start and last-seen locations must be known campus locations.")
    probabilities = _validate_probabilities(data.get("probabilities"), candidates)
    algorithm, heuristic = _search_configuration(data)
    blocked_input = data.get("blocked_edges", [])
    if not isinstance(blocked_input, list):
        raise ValueError("'blocked_edges' must be a list.")
    campus, blocked_edges = _campus_with_blocks(blocked_input)
    planner = CandidatePlanner(campus, algorithm=algorithm, heuristic=heuristic)
    results = planner.plan(start, candidates, probabilities)
    visit_order = planner.recommended_visit_order(results, start=start)
    mode = data.get("mode", "plan")
    if mode not in ("plan", "mission"):
        raise ValueError("'mode' must be plan or mission.")

    path: list[str] = []
    explored: list[str] = []
    selected_search: dict[str, Any] | None = None
    mission: list[dict[str, Any]] = []
    recovered_location: str | None = None
    if mode == "mission":
        actual_location = _required_text(data, "actual_location")
        if actual_location not in candidates:
            raise ValueError("The simulated item location must be one of the candidates.")
        steps = planner.execute_mission(start, visit_order, actual_location)
        for step in steps:
            mission.append(_mission_step(step, str(data.get("item_description", "Item"))))
            result = step.algorithm_result
            if result.success:
                path.extend(result.path if not path else result.path[1:])
            explored.extend(result.explored_nodes)
            if step.item_found:
                recovered_location = step.candidate
        if steps:
            selected_search = _search_result(steps[-1].algorithm_result)
    else:
        best = next((result for result in results if result.reachable), None)
        if best:
            selected_search = _search_result(best.algorithm_result)
            path = best.path
            explored = best.algorithm_result.explored_nodes

    return jsonify({
        "mode": mode,
        "item_description": str(data.get("item_description", "Item")),
        "start": start,
        "last_seen": last_seen,
        "algorithm": algorithm,
        "blocked_edges": blocked_edges,
        "candidate_results": [_candidate_result(result) for result in results],
        "visit_order": visit_order,
        "tour": [start, *visit_order],
        "selected_search": selected_search,
        "path": path,
        "explored_nodes": list(dict.fromkeys(explored)),
        "mission": mission,
        "recovered_location": recovered_location,
    })


@app.post("/api/compare")
def compare_algorithms():
    data = request.get_json(silent=False)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    start = _required_text(data, "start")
    goal = _required_text(data, "goal")
    campus, _ = _campus_with_blocks(data.get("blocked_edges", []))
    if not campus.has_node(start) or not campus.has_node(goal):
        raise ValueError("Start and goal must be known campus locations.")
    return jsonify({
        "results": [
            _search_result(bfs(campus, start, goal)),
            _search_result(greedy_best_first(campus, start, goal, euclidean_distance)),
            _search_result(astar(campus, start, goal, euclidean_distance)),
        ]
    })


@app.post("/api/search/grid")
def search_grid():
    data = request.get_json(silent=False)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    rows = _bounded_int(data, "rows", 5, 50)
    cols = _bounded_int(data, "cols", 5, 50)
    density = data.get("density", 0.15)
    if isinstance(density, bool) or not isinstance(density, (int, float)):
        raise ValueError("'density' must be a number between 0 and 0.4.")
    if not math.isfinite(density) or not 0 <= density <= 0.4:
        raise ValueError("'density' must be between 0 and 0.4.")
    seed = _bounded_int(data, "seed", 0, 2**31 - 1)
    start = _required_text(data, "start")
    goal = _required_text(data, "goal")
    algorithm, _ = _search_configuration(data)
    grid = GridMap.from_obstacle_density(rows, cols, float(density), seed=seed)
    for name in (start, goal):
        row, col = GridMap.name_to_pos(name)
        if not grid.in_bounds(row, col):
            raise ValueError(f"Grid point '{name}' is outside the selected grid.")
        grid.clear_obstacle(row, col)

    if algorithm == "bfs":
        result = bfs(grid, start, goal)
    elif algorithm == "greedy":
        result = greedy_best_first(grid, start, goal, manhattan_distance)
    else:
        result = astar(grid, start, goal, manhattan_distance)
    return jsonify({
        "rows": rows,
        "cols": cols,
        "seed": seed,
        "obstacles": [
            [row, col]
            for row in range(rows)
            for col in range(cols)
            if grid.is_obstacle(row, col)
        ],
        "search": _search_result(result),
    })


def _bounded_int(data: dict[str, Any], name: str, minimum: int, maximum: int) -> int:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"'{name}' must be an integer from {minimum} to {maximum}.")
    return value


@app.post("/api/benchmarks")
def run_benchmarks():
    from benchmark.scenarios import FAST_SCENARIOS, SCENARIOS, BenchmarkScenario

    try:
        remote = ip_address(request.remote_addr)
    except ValueError:
        abort(403, description="Benchmarking is available only from localhost.")
    if not remote.is_loopback:
        abort(403, description="Benchmarking is available only from localhost.")

    data = request.get_json(silent=False)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")
    suite = data.get("suite", "fast")
    trials = _bounded_int(data, "trials", 1, 10)
    if not isinstance(suite, str):
        raise ValueError("'suite' must be fast, standard, or custom.")
    if suite == "fast":
        scenarios = FAST_SCENARIOS
    elif suite == "standard":
        scenarios = SCENARIOS
    elif suite == "custom":
        rows = _bounded_int(data, "rows", 5, 50)
        cols = _bounded_int(data, "cols", 5, 50)
        density = data.get("density", 0.2)
        if isinstance(density, bool) or not isinstance(density, (int, float)):
            raise ValueError("'density' must be a number between 0 and 0.4.")
        if not math.isfinite(density) or not 0 <= density <= 0.4:
            raise ValueError("'density' must be between 0 and 0.4.")
        scenarios = [BenchmarkScenario(
            name=f"Custom-{rows}x{cols}",
            rows=rows,
            cols=cols,
            obstacle_density=float(density),
            seed=_bounded_int(data, "seed", 0, 2**31 - 1),
            num_trials=trials,
            description="User-configured grid.",
        )]
    else:
        raise ValueError("'suite' must be fast, standard, or custom.")

    configured = [
        replace(scenario, num_trials=trials)
        for scenario in scenarios
    ]
    try:
        result = _run_benchmarks_with_timeout(configured)
    except TimeoutError as error:
        return jsonify({"error": str(error)}), 504
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
