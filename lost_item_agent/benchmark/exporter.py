"""
benchmark/exporter.py
---------------------
CSV export and summary statistics for benchmark DataFrames.

All functions accept a pandas DataFrame in the format produced by
BenchmarkRunner.run_all() and are pure (no side-effects except file I/O
in export_csv).
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(df: pd.DataFrame, filepath: str | os.PathLike) -> Path:
    """
    Write a benchmark DataFrame to a CSV file.

    Parameters
    ----------
    df : pd.DataFrame
        Output of BenchmarkRunner.run_all().
    filepath : str | Path
        Destination path.  Parent directories are created if needed.

    Returns
    -------
    Path
        Resolved absolute path of the written file.

    Raises
    ------
    ValueError
        If df is empty.
    """
    if df.empty:
        raise ValueError("Cannot export an empty DataFrame.")

    path = Path(filepath).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate benchmark results by (scenario_name, algorithm).

    For each group, compute mean, min, and max of the key numeric metrics.
    Failed trials are counted in success_rate. Path cost and path length
    means use successful trials only; node counts and runtime include every
    attempted trial because they measure search effort.

    Parameters
    ----------
    df : pd.DataFrame
        Raw output of BenchmarkRunner.run_all().

    Returns
    -------
    pd.DataFrame
        One row per (scenario_name, algorithm) with columns:
          scenario_name, algorithm, total_trials, success_count,
          success_rate,
          mean/min/max for: execution_time_ms, nodes_expanded,
          nodes_generated, path_cost, path_length.

    Notes
    -----
    Failed path_cost/path_length values are NaN and excluded by pandas
    aggregations. Nodes expanded/generated and runtime are measured for
    both successful and failed trials.
    """
    if df.empty:
        return pd.DataFrame()

    metric_cols = [
        "execution_time_ms",
        "nodes_expanded",
        "nodes_generated",
        "path_cost",
        "path_length",
    ]

    rows: list[dict] = []
    for (scenario, algo), group in df.groupby(
        ["scenario_name", "algorithm"], sort=False
    ):
        total = len(group)
        success_count = int(group["success"].sum())

        row: dict = {
            "scenario_name": scenario,
            "algorithm": algo,
            "total_trials": total,
            "success_count": success_count,
            "success_rate": success_count / total if total > 0 else float("nan"),
        }
        for metadata_col in ("map_mode", "grid_size", "obstacle_density"):
            if metadata_col in group.columns:
                row[metadata_col] = group[metadata_col].iloc[0]

        for col in metric_cols:
            if col in group.columns:
                valid = group[col].dropna()
                row[f"mean_{col}"] = valid.mean() if not valid.empty else float("nan")
                row[f"min_{col}"] = valid.min() if not valid.empty else float("nan")
                row[f"max_{col}"] = valid.max() if not valid.empty else float("nan")

        rows.append(row)

    summary = pd.DataFrame(rows)

    # Consistent algorithm ordering for display
    algo_order = {"BFS": 0, "Greedy": 1, "A*": 2}
    if "algorithm" in summary.columns:
        summary["_algo_sort"] = summary["algorithm"].map(
            lambda a: algo_order.get(a, 99)
        )
        summary = summary.sort_values(
            ["scenario_name", "_algo_sort"]
        ).drop(columns=["_algo_sort"])

    return summary.reset_index(drop=True)


def summary_export_csv(df: pd.DataFrame, filepath: str | os.PathLike) -> Path:
    """Summarize then export to CSV."""
    summary = summarize(df)
    return export_csv(summary, filepath)


# ---------------------------------------------------------------------------
# Pivot helpers (for chart_viz)
# ---------------------------------------------------------------------------

def pivot_metric(
    summary: pd.DataFrame,
    metric: str,
    agg: str = "mean",
) -> pd.DataFrame:
    """
    Pivot summary DataFrame for easy bar-chart plotting.

    Parameters
    ----------
    summary : pd.DataFrame
        Output of summarize().
    metric : str
        Base metric name, e.g. "execution_time_ms".
    agg : str
        Aggregation prefix: "mean", "min", or "max".

    Returns
    -------
    pd.DataFrame
        Index = scenario_name, columns = algorithm names,
        values = metric values.
    """
    col = f"{agg}_{metric}"
    if col not in summary.columns:
        raise ValueError(f"Column '{col}' not found in summary DataFrame.")

    pivot = summary.pivot(index="scenario_name", columns="algorithm", values=col)
    # Ensure consistent column ordering
    cols_ordered = [c for c in ["BFS", "Greedy", "A*"] if c in pivot.columns]
    return pivot[cols_ordered]
