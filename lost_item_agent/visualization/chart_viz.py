"""
visualization/chart_viz.py
--------------------------
Matplotlib comparison charts for benchmark results.

All functions return a ``matplotlib.figure.Figure`` object so callers can
display or save charts independently.

Chart catalogue
~~~~~~~~~~~~~~~
draw_bar_comparison    Side-by-side bar chart for one metric across scenarios.
draw_scaling_lines     Line chart: metric vs grid_size for each algorithm.
draw_boxplot           Box-and-whisker distribution of a metric per algorithm.
draw_success_rate      Grouped bar chart for success rate per scenario.
draw_algorithm_radar   Radar (spider) chart summarising multiple metrics.

All charts
~~~~~~~~~~
* Use a consistent colour palette (BFS=blue, Greedy=orange, A*=green).
* Include axis labels, titles, and legends.
* Do not hard-code any numeric results.
* Are readable at 800×500 px (default figure size).
"""

from __future__ import annotations

import math
from typing import Optional

import matplotlib
matplotlib.use("Agg")   # Non-interactive backend for tests and file output.
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from benchmark.exporter import pivot_metric

# Consistent colour palette keyed by algorithm name
ALGO_COLOURS: dict[str, str] = {
    "BFS":    "#4C72B0",   # muted blue
    "Greedy": "#DD8452",   # muted orange
    "A*":     "#55A868",   # muted green
}
ALGO_ORDER = ["BFS", "Greedy", "A*"]


# ---------------------------------------------------------------------------
# 1. Side-by-side bar comparison
# ---------------------------------------------------------------------------

def draw_bar_comparison(
    summary: pd.DataFrame,
    metric: str,
    agg: str = "mean",
    title: Optional[str] = None,
    ylabel: Optional[str] = None,
    figsize: tuple[float, float] = (10, 5),
) -> plt.Figure:
    """
    Side-by-side grouped bar chart comparing BFS, Greedy, and A*
    across all scenarios for a single metric.

    Parameters
    ----------
    summary : pd.DataFrame
        Output of benchmark.exporter.summarize().
    metric : str
        One of: execution_time_ms, nodes_expanded, nodes_generated,
        path_cost, path_length.
    agg : str
        "mean", "min", or "max".
    title : str, optional
        Chart title.  Defaults to a generated title.
    ylabel : str, optional
        Y-axis label.  Defaults to ``f"{agg} {metric}"``.
    """
    pivot = pivot_metric(summary, metric, agg)
    scenarios = list(pivot.index)
    algorithms = [a for a in ALGO_ORDER if a in pivot.columns]

    n_scenarios = len(scenarios)
    n_algos = len(algorithms)
    x = np.arange(n_scenarios)
    width = 0.25
    offsets = np.linspace(-(n_algos - 1) / 2, (n_algos - 1) / 2, n_algos) * width

    fig, ax = plt.subplots(figsize=figsize)

    for i, algo in enumerate(algorithms):
        values = pivot[algo].values
        bars = ax.bar(
            x + offsets[i],
            values,
            width=width,
            label=algo,
            color=ALGO_COLOURS.get(algo, "#888888"),
            edgecolor="white",
            linewidth=0.5,
        )
        # Value labels on bars
        for bar, val in zip(bars, values):
            if not math.isnan(val):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() * 1.01,
                    f"{val:.2f}" if val < 100 else f"{int(val)}",
                    ha="center", va="bottom", fontsize=7,
                )

    col_label = f"{agg} {metric}".replace("_", " ")
    ax.set_xlabel("Scenario", fontsize=11)
    ax.set_ylabel(ylabel or col_label, fontsize=11)
    ax.set_title(title or f"Algorithm Comparison — {col_label}", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=9)
    ax.legend(title="Algorithm", fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.1f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 2. Scaling line chart (metric vs grid size)
# ---------------------------------------------------------------------------

def draw_scaling_lines(
    summary: pd.DataFrame,
    metric: str,
    agg: str = "mean",
    title: Optional[str] = None,
    figsize: tuple[float, float] = (9, 5),
) -> plt.Figure:
    """
    Line chart showing how a metric scales with grid_size for grid scenarios.

    Campus scenarios are excluded (no meaningful grid_size).
    """
    metric_col = f"{agg}_{metric}"
    if "grid_size" in summary.columns and metric_col in summary.columns:
        data = summary.loc[summary["grid_size"] > 0].copy()
        data["value"] = data[metric_col]
    elif {"scenario_name", "algorithm", "grid_size", metric}.issubset(summary.columns):
        raw = summary.loc[summary["grid_size"] > 0]
        data = (
            raw.groupby(
                ["scenario_name", "algorithm", "grid_size"],
                as_index=False,
                sort=False,
            )[metric]
            .mean()
            .rename(columns={metric: "value"})
        )
    else:
        data = pd.DataFrame()

    if data.empty:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No grid scenarios available", ha="center", va="center")
        return fig

    fig, ax = plt.subplots(figsize=figsize)

    algorithms = [a for a in ALGO_ORDER if a in data["algorithm"].unique()]

    for algo in algorithms:
        algo_data = data[data["algorithm"] == algo].sort_values("grid_size")
        xs = algo_data["grid_size"].tolist()
        ys = algo_data["value"].tolist()
        ax.plot(
            xs, ys,
            marker="o",
            label=algo,
            color=ALGO_COLOURS.get(algo, "#888888"),
            linewidth=2,
            markersize=7,
        )
        for x, y in zip(xs, ys):
            if not math.isnan(y):
                ax.annotate(
                    f"{y:.1f}" if y < 1000 else f"{int(y):,}",
                    (x, y),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=7,
                )

    col_label = f"{agg} {metric}".replace("_", " ")
    ax.set_xlabel("Grid Size (cells)", fontsize=11)
    ax.set_ylabel(col_label, fontsize=11)
    ax.set_title(title or f"Scaling: {col_label} vs Grid Size", fontsize=13, fontweight="bold")
    ax.legend(title="Algorithm", fontsize=9)
    ax.grid(linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=15, ha="right", fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 3. Box-and-whisker distribution
# ---------------------------------------------------------------------------

def draw_boxplot(
    raw_df: pd.DataFrame,
    metric: str,
    scenario_name: Optional[str] = None,
    title: Optional[str] = None,
    figsize: tuple[float, float] = (8, 5),
) -> plt.Figure:
    """
    Box plot showing the distribution of a metric across trials,
    grouped by algorithm.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Raw output of BenchmarkRunner.run_all() (not the summary).
    metric : str
        Column name in raw_df.
    scenario_name : str, optional
        Filter to one scenario.  If None, use all scenarios.
    """
    df = raw_df.copy()
    if scenario_name:
        df = df[df["scenario_name"] == scenario_name]

    if df.empty or metric not in df.columns:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        return fig

    fig, ax = plt.subplots(figsize=figsize)
    algorithms = [a for a in ALGO_ORDER if a in df["algorithm"].unique()]
    data_groups = [df[df["algorithm"] == a][metric].dropna().tolist() for a in algorithms]

    try:
        bp = ax.boxplot(
            data_groups,
            tick_labels=algorithms,
            patch_artist=True,
            medianprops={"color": "black", "linewidth": 2},
            whiskerprops={"linewidth": 1.5},
            capprops={"linewidth": 1.5},
        )
    except TypeError:
        bp = ax.boxplot(
            data_groups,
            labels=algorithms,
            patch_artist=True,
            medianprops={"color": "black", "linewidth": 2},
            whiskerprops={"linewidth": 1.5},
            capprops={"linewidth": 1.5},
        )
    for patch, algo in zip(bp["boxes"], algorithms):
        patch.set_facecolor(ALGO_COLOURS.get(algo, "#888888"))
        patch.set_alpha(0.7)

    label = metric.replace("_", " ")
    scenario_label = f" — {scenario_name}" if scenario_name else ""
    ax.set_xlabel("Algorithm", fontsize=11)
    ax.set_ylabel(label, fontsize=11)
    ax.set_title(title or f"Distribution: {label}{scenario_label}", fontsize=13, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4. Success rate grouped bar
# ---------------------------------------------------------------------------

def draw_success_rate(
    summary: pd.DataFrame,
    title: Optional[str] = None,
    figsize: tuple[float, float] = (10, 5),
) -> plt.Figure:
    """
    Grouped bar chart showing success rate (0–1) per scenario per algorithm.
    """
    if summary.empty or "success_rate" not in summary.columns:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        return fig

    pivot = summary.pivot(
        index="scenario_name", columns="algorithm", values="success_rate"
    )
    algorithms = [a for a in ALGO_ORDER if a in pivot.columns]
    pivot = pivot[algorithms]

    scenarios = list(pivot.index)
    n_scenarios = len(scenarios)
    n_algos = len(algorithms)
    x = np.arange(n_scenarios)
    width = 0.25
    offsets = np.linspace(-(n_algos - 1) / 2, (n_algos - 1) / 2, n_algos) * width

    fig, ax = plt.subplots(figsize=figsize)
    for i, algo in enumerate(algorithms):
        values = pivot[algo].values
        bars = ax.bar(
            x + offsets[i],
            values,
            width=width,
            label=algo,
            color=ALGO_COLOURS.get(algo, "#888888"),
            edgecolor="white",
        )
        for bar, val in zip(bars, values):
            if not math.isnan(val):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.01,
                    f"{val:.0%}",
                    ha="center", va="bottom", fontsize=8,
                )

    ax.set_xlabel("Scenario", fontsize=11)
    ax.set_ylabel("Success Rate", fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_title(title or "Success Rate by Scenario and Algorithm", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=9)
    ax.legend(title="Algorithm", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5. Multi-metric summary table (returns styled DataFrame, not figure)
# ---------------------------------------------------------------------------

def build_comparison_table(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Build a human-readable comparison table for display.

    Returns a DataFrame with rounded values suitable for st.dataframe() or
    to_html() rendering.  Not a chart — returns a DataFrame, not a Figure.
    """
    cols = [
        "scenario_name", "algorithm", "success_rate",
        "mean_execution_time_ms", "mean_nodes_expanded",
        "mean_nodes_generated", "mean_path_cost", "mean_path_length",
    ]
    present = [c for c in cols if c in summary.columns]
    display = summary[present].copy()

    # Round floats for readability
    float_cols = [c for c in present if c.startswith("mean_") or c == "success_rate"]
    for col in float_cols:
        display[col] = display[col].round(3)

    display.columns = [
        c.replace("mean_", "avg_").replace("_", " ").title()
        for c in present
    ]
    return display.reset_index(drop=True)
