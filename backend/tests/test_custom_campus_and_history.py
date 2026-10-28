"""
backend/tests/test_custom_campus_and_history.py
------------------------------------------------
Tests for dynamic campus configuration, custom nodes/edges, heuristic verification API,
and search/mission history tracking.
"""

import pytest
from web.server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_custom_campus_and_reset(client):
    # Configure a custom campus with 3 nodes
    payload = {
        "nodes": [
            {"name": "Gate-A", "row": 0, "col": 0, "node_type": "corridor", "search_cost": 1.0, "x": 1.0, "y": 1.0, "floor": "Ground floor"},
            {"name": "Plaza", "row": 0, "col": 1, "node_type": "generic", "search_cost": 2.0, "x": 2.0, "y": 1.0, "floor": "Ground floor"},
            {"name": "Auditorium", "row": 1, "col": 1, "node_type": "classroom", "search_cost": 4.0, "x": 2.0, "y": 2.5, "floor": "Ground floor"},
        ],
        "edges": [
            {"source": "Gate-A", "target": "Plaza", "weight": 2.0},
            {"source": "Plaza", "target": "Auditorium", "weight": 3.0},
        ],
    }
    resp = client.post("/api/campus/custom", json=payload)
    assert resp.status_code == 200
    data = resp.json
    assert data["is_custom_campus"] is True
    assert "Gate-A" in data["locations"]
    assert "Auditorium" in data["locations"]
    assert len(data["nodes"]) == 3

    # Plan on custom campus
    plan_resp = client.post("/api/search/campus", json={
        "start": "Gate-A",
        "last_seen": "Auditorium",
        "candidates": ["Auditorium"],
        "visited": [],
    })
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json
    assert plan_data["tour"] == ["Gate-A", "Auditorium"]
    assert plan_data["path"] == ["Gate-A", "Plaza", "Auditorium"]

    # Verify heuristic API works on custom campus
    vh_resp = client.post("/api/campus/verify_heuristic")
    assert vh_resp.status_code == 200
    vh_data = vh_resp.json
    assert vh_data["admissible"] is True
    assert vh_data["consistent"] is True

    # Reset back to default
    reset_resp = client.post("/api/campus/reset")
    assert reset_resp.status_code == 200
    reset_data = reset_resp.json
    assert reset_data["is_custom_campus"] is False
    assert "Main Entrance" in reset_data["locations"]
    assert "Auditorium" not in reset_data["locations"]


def test_search_history_api(client):
    # Clear history
    del_resp = client.delete("/api/history")
    assert del_resp.status_code == 200

    # Execute a search to populate history
    client.post("/api/search/campus", json={
        "start": "Main Entrance",
        "last_seen": "Library",
        "candidates": ["Library", "Canteen"],
        "visited": [],
        "item_description": "Red Notebook",
    })

    # Fetch history
    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json["history"]
    assert len(history) >= 1
    assert history[0]["item"] == "Red Notebook"
    assert history[0]["start"] == "Main Entrance"
    assert history[0]["last_seen"] == "Library"

    # Post explicit custom entry
    client.post("/api/history", json={
        "item": "Test Item",
        "start": "Reception",
        "last_seen": "Parking",
    })
    hist_resp2 = client.get("/api/history")
    assert any(h.get("item") == "Test Item" for h in hist_resp2.json["history"])
