"""
search/result.py
----------------
Re-exports SearchResult from environment.models so search modules have a
single clean import path.

    from search.result import SearchResult
"""

from environment.models import SearchResult  # noqa: F401  (re-export)
