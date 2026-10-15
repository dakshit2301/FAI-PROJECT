"""
app.py
------
Root-level entry point for the Lost Item Recovery Agent Streamlit Application.
Delegates to lost_item_agent/app/main.py.

Allows starting the application directly from the repository root with:
    streamlit run app.py
or running with:
    streamlit run lost_item_agent/app.py
    streamlit run lost_item_agent/app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure lost_item_agent package directory is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = PROJECT_ROOT / "lost_item_agent"

if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

# Expose app package directory to allow package attribute resolution
__path__ = [str(PACKAGE_DIR / "app")]

from app.main import main

if __name__ == "__main__":
    main()
