"""API and static website tests for the Flask application."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from web.server import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_website_and_health_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Lost Item Recovery Agent" in response.data
    assert b"/static/app.js" in response.data
    assert client.get("/api/health").json == {"status": "ok"}


def test_config_contains_campus_graph_and_item_suggestions(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    config = response.json
    assert len(config["locations"]) == 20
    assert len(config["edges"]) == 26
    assert "laptop" in config["item_candidates"]
    assert {"name", "x", "y", "floor"} <= config["nodes"][0].keys()


def test_campus_plan_returns_ranked_candidates_and_route(client):
    response = client.post("/api/search/campus", json={
        "start": "Main Entrance",
        "last_seen": "Library",
        "candidates": ["Library", "Lab-A"],
        "visited": ["Reception"],
        "probabilities": {"Library": 0.8, "Lab-A": 0.4, "Reception": 0.5},
        "algorithm": "astar",
        "heuristic": "euclidean",
        "mode": "plan",
    })
    assert response.status_code == 200
    result = response.json
    assert len(result["candidate_results"]) == 3
    assert result["candidate_results"][0]["rank"] == 1
    assert result["tour"][0] == "Main Entrance"
    assert result["selected_search"]["success"] is True
    assert result["path"][0] == "Main Entrance"


def test_campus_mission_stops_at_simulated_item_location(client):
    response = client.post("/api/search/campus", json={
        "start": "Main Entrance",
        "last_seen": "Main Entrance",
        "candidates": ["Library", "Lab-A"],
        "visited": [],
        "algorithm": "astar",
        "heuristic": "euclidean",
        "actual_location": "Library",
        "item_description": "laptop",
        "mode": "mission",
    })
    assert response.status_code == 200
    result = response.json
    assert result["recovered_location"] == "Library"
    assert result["mission"][-1]["found"] is True
    assert result["path"][0] == "Main Entrance"
    assert result["path"][-1] == "Library"


def test_campus_search_rejects_empty_candidates_and_invalid_edges(client):
    empty = client.post("/api/search/campus", json={
        "start": "Main Entrance",
        "last_seen": "Library",
        "candidates": [],
        "visited": [],
    })
    invalid_edge = client.post("/api/search/campus", json={
        "start": "Main Entrance",
        "last_seen": "Library",
        "candidates": ["Library"],
        "blocked_edges": [["Main Entrance", "Library"]],
    })
    assert empty.status_code == 400
    assert "at least one" in empty.json["error"]
    assert invalid_edge.status_code == 400
    assert "No campus corridor" in invalid_edge.json["error"]


def test_api_http_errors_return_json_and_keep_status(client):
    malformed_json = client.post(
        "/api/search/campus",
        data='{"start":',
        content_type="application/json",
    )
    unsupported_media_type = client.post(
        "/api/search/campus",
        data="{}",
        content_type="text/plain",
    )

    assert malformed_json.status_code == 400
    assert malformed_json.is_json
    assert malformed_json.json["status"] == 400
    assert malformed_json.json["error"]
    assert unsupported_media_type.status_code == 415
    assert unsupported_media_type.is_json
    assert unsupported_media_type.json["status"] == 415
    assert unsupported_media_type.json["error"]


def test_non_api_http_errors_keep_default_html_response(client):
    response = client.get("/missing-page")

    assert response.status_code == 404
    assert not response.is_json


def test_comparison_runs_all_algorithms_for_same_pair(client):
    response = client.post("/api/compare", json={
        "start": "Main Entrance",
        "goal": "Classroom-102",
    })
    assert response.status_code == 200
    results = response.json["results"]
    assert [result["algorithm"] for result in results] == ["BFS", "Greedy", "A*"]
    assert all(result["success"] for result in results)


def test_grid_search_is_seeded_and_keeps_endpoints_walkable(client):
    payload = {
        "rows": 10,
        "cols": 10,
        "density": 0.3,
        "seed": 33,
        "algorithm": "astar",
        "start": "(0,0)",
        "goal": "(9,9)",
    }
    first = client.post("/api/search/grid", json=payload)
    second = client.post("/api/search/grid", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json["obstacles"] == second.json["obstacles"]
    assert first.json["search"]["path"][0] == "(0,0)"
    assert first.json["search"]["path"][-1] == "(9,9)"


@pytest.mark.parametrize("payload", [
    {"rows": 2, "cols": 10, "density": 0.1, "seed": 1, "algorithm": "astar", "start": "(0,0)", "goal": "(1,9)"},
    {"rows": 10, "cols": 10, "density": 0.8, "seed": 1, "algorithm": "astar", "start": "(0,0)", "goal": "(9,9)"},
    {"rows": 10, "cols": 10, "density": 0.1, "seed": 1, "algorithm": "invalid", "start": "(0,0)", "goal": "(9,9)"},
])
def test_grid_search_rejects_invalid_inputs(client, payload):
    response = client.post("/api/search/grid", json=payload)
    assert response.status_code == 400
    assert "error" in response.json


def test_quick_benchmark_returns_summary_and_csv(client):
    response = client.post("/api/benchmarks", json={"suite": "fast", "trials": 1})
    assert response.status_code == 200
    data = response.json
    assert len(data["summary"]) == 9
    assert data["raw_csv"].startswith("scenario_name,map_mode,grid_size,obstacle_density,algorithm,")
    assert data["summary_csv"].startswith("scenario_name,algorithm,total_trials")
    assert {"BFS", "Greedy", "A*"} == {row["algorithm"] for row in data["summary"]}


def test_benchmark_endpoint_rejects_non_loopback_clients(client, monkeypatch):
    def benchmark_must_not_run(_scenarios):
        pytest.fail("Non-local client must not start a benchmark.")

    monkeypatch.setattr("web.server._run_benchmarks_with_timeout", benchmark_must_not_run)
    response = client.post(
        "/api/benchmarks",
        json={"suite": "fast", "trials": 1},
        environ_overrides={"REMOTE_ADDR": "203.0.113.8"},
    )

    assert response.status_code == 403
    assert response.is_json
    assert response.json["status"] == 403


def test_benchmark_endpoint_allows_ipv4_mapped_loopback(client, monkeypatch):
    monkeypatch.setattr("web.server._run_benchmarks_with_timeout", lambda _scenarios: {"ok": True})
    response = client.post(
        "/api/benchmarks",
        json={"suite": "fast", "trials": 1},
        environ_overrides={"REMOTE_ADDR": "::ffff:127.0.0.1"},
    )

    assert response.status_code == 200
    assert response.json == {"ok": True}


def test_benchmark_endpoint_reports_timeout_as_gateway_timeout(client, monkeypatch):
    def timed_out(_scenarios):
        raise TimeoutError("Benchmark exceeded the test time limit.")

    monkeypatch.setattr("web.server._run_benchmarks_with_timeout", timed_out)
    response = client.post("/api/benchmarks", json={"suite": "fast", "trials": 1})

    assert response.status_code == 504
    assert response.is_json
    assert "time limit" in response.json["error"]


def test_benchmark_timeout_terminates_worker(monkeypatch):
    import web.server as server_module
    from benchmark.scenarios import BenchmarkScenario

    monkeypatch.setattr(server_module, "BENCHMARK_TIMEOUT_SECONDS", 0.001)
    scenario = BenchmarkScenario(
        name="Timeout-test",
        rows=50,
        cols=50,
        obstacle_density=0.2,
        seed=1,
        num_trials=10,
    )
    start = time.monotonic()

    with pytest.raises(TimeoutError, match="time limit"):
        server_module._run_benchmarks_with_timeout([scenario])

    assert time.monotonic() - start < 5
