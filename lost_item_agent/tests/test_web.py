"""API and static website tests for the Flask application."""

from __future__ import annotations

import sys
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
