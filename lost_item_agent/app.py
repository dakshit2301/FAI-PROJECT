"""
app.py
------
Root-level entry point for the Lost Item Recovery Agent Streamlit Application.
Delegates to app.main.main().

Allows starting the application with either:
    streamlit run app.py
or
    streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Expose app package directory to allow package attribute resolution
__path__ = [str(PROJECT_ROOT / "app")]

from app.main import main

if __name__ == "__main__":
    main()
