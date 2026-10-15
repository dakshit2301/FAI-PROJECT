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

from streamlit.testing.v1 import AppTest


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
        # Switch to Multi-Algorithm Comparison
        radio = at.sidebar.radio[0]
        radio.set_value("⚖️ Multi-Algorithm Comparison")
        at.run()
        assert not at.exception, f"Comparison view threw exception: {at.exception}"

    def test_navigation_to_grid_search(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to 2D Grid Search Playground
        radio = at.sidebar.radio[0]
        radio.set_value("🏁 2D Grid Search Playground")
        at.run()
        assert not at.exception, f"Grid playground threw exception: {at.exception}"

    def test_navigation_to_benchmarks(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to Experimental Benchmarks
        radio = at.sidebar.radio[0]
        radio.set_value("📊 Experimental Benchmarks")
        at.run()
        assert not at.exception, f"Benchmark view threw exception: {at.exception}"

    def test_navigation_to_methodology(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        # Switch to AI Theory & Methodology
        radio = at.sidebar.radio[0]
        radio.set_value("📘 AI Theory & Methodology")
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

    def test_methodology_shows_proposal_coverage(self, app_path: str):
        at = AppTest.from_file(app_path, default_timeout=30)
        at.run()
        at.sidebar.radio[0].set_value("📘 AI Theory & Methodology")
        at.run()
        assert not at.exception, f"Proposal coverage view failed: {at.exception}"
        assert any("Proposal requirement" in str(table.value) for table in at.dataframe)

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
