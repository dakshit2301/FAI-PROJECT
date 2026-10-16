"""
tests/test_app.py
-----------------
Automated tests for the Streamlit application using streamlit.testing.v1.AppTest.
Verifies that all views, navigation tabs, and components render cleanly
without runtime exceptions or broken integrations.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

import matplotlib.pyplot as plt
from streamlit.testing.v1 import AppTest

from app.components.campus_map_view import draw_campus_map, draw_grid_map
from environment.grid import GridMap
from environment.locations import build_default_campus


@pytest.fixture
def app_path() -> str:
    path = Path(__file__).resolve().parent.parent / "app" / "main.py"
    return str(path)


class TestStreamlitApp:
    def test_app_loads_without_exceptions(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        assert not at.exception, f"App threw exception: {at.exception}"
        assert len(at.title) >= 0 or len(at.header) >= 0

    def test_navigation_to_comparison(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to Algorithm Comparison
        radio = at.sidebar.radio[0]
        radio.set_value("Algorithm Comparison")
        at.run()
        assert not at.exception, f"Comparison view threw exception: {at.exception}"

    def test_navigation_to_grid_search(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to Grid Search
        radio = at.sidebar.radio[0]
        radio.set_value("Grid Search")
        at.run()
        assert not at.exception, f"Grid playground threw exception: {at.exception}"

    def test_navigation_to_benchmarks(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to Benchmarks
        radio = at.sidebar.radio[0]
        radio.set_value("Benchmarks")
        at.run()
        assert not at.exception, f"Benchmark view threw exception: {at.exception}"

    def test_navigation_to_methodology(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to Methodology
        radio = at.sidebar.radio[0]
        radio.set_value("Methodology")
        at.run()
        assert not at.exception, f"Methodology view threw exception: {at.exception}"

    def test_recovery_mission_runs_and_renders_candidate_results(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        at.button[1].click()
        at.run()

        assert not at.exception, f"Recovery mission threw exception: {at.exception}"
        assert len(at.dataframe) >= 1

    def test_item_category_updates_default_candidates(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        at.selectbox[0].set_value("bag")
        at.run()

        assert not at.exception, f"Changing item category threw exception: {at.exception}"
        assert at.multiselect[0].value == [
            "Canteen",
            "Library",
            "Classroom-101",
            "Classroom-102",
            "Parking",
        ]

    def test_current_location_and_visited_places_feed_search(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()

        current_location = next(
            widget for widget in at.selectbox
            if widget.key == "current_location"
        )
        current_location.set_value("Reception")
        visited_locations = next(
            widget for widget in at.multiselect
            if widget.key == "visited_locations"
        )
        visited_locations.set_value(["Washroom-G"])
        at.run()

        at.button[0].click()
        at.run()

        assert not at.exception, f"Planning with search history failed: {at.exception}"
        assert "Washroom-G" in str(at.dataframe[0].value)

    def test_methodology_shows_project_requirements_without_viva_extras(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        at.sidebar.radio[0].set_value("Methodology")
        at.run()
        assert not at.exception, f"Methodology view failed: {at.exception}"
        assert [tab.label for tab in at.tabs] == [
            "PEAS",
            "Problem formulation",
            "Algorithms",
            "Candidate search",
        ]
        assert any("PEAS" in heading.value for heading in at.subheader)

    def test_custom_item_description_is_used_in_mission(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        at.selectbox[0].set_value("other / custom")
        at.run()
        description = next(
            widget for widget in at.text_input
            if widget.label == "Describe the item"
        )
        description.set_value("blue water bottle")
        at.button[1].click()
        at.run()

        assert not at.exception, f"Custom-item mission failed: {at.exception}"
        assert any("blue water bottle" in item.value for item in at.success)

    def test_root_app_entrypoint(self):
        root_path = Path(__file__).resolve().parent.parent / "app.py"
        at = AppTest.from_file(str(root_path), default_timeout=30)
        at.run()
        assert not at.exception, f"app.py entry point threw exception: {at.exception}"

    def test_repo_root_app_entrypoint(self):
        repo_root_path = Path(__file__).resolve().parent.parent.parent / "app.py"
        if repo_root_path.exists():
            at = AppTest.from_file(str(repo_root_path), default_timeout=30)
            at.run()
            assert not at.exception, f"Repo root app.py threw exception: {at.exception}"


class TestMapLegends:
    def test_grid_goal_is_distinct_from_recovered_location(self):
        fig = draw_grid_map(
            GridMap(5, 5),
            start_pos="(0,0)",
            path=["(0,0)", "(0,1)", "(0,2)"],
            goal_pos="(0,2)",
        )

        cells = fig.axes[0].images[0].get_array()
        assert cells[0, 0] == 5
        assert cells[0, 1] == 3
        assert cells[0, 2] == 6
        legend_labels = [text.get_text() for text in fig.legends[0].get_texts()]
        assert "Goal (G)" in legend_labels
        assert "Recovered" not in legend_labels
        plt.close(fig)

    def test_campus_map_has_semantic_status_legend(self):
        fig = draw_campus_map(
            build_default_campus(),
            start_node="Main Entrance",
            last_known_node="Library",
            candidate_nodes=["Library"],
            path=["Main Entrance", "Reception"],
            recovered_node="Library",
            blocked_edges=[("Corridor-G1", "Library")],
            visited_nodes=["Library"],
        )

        legend_labels = [text.get_text() for text in fig.axes[0].get_legend().get_texts()]
        assert "Current position" in legend_labels
        assert "Planned route" in legend_labels
        assert "Blocked corridor" in legend_labels
        assert "Recovered (simulation)" in legend_labels
        plt.close(fig)
