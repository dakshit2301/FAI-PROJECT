"""
app/components/campus_map_view.py
---------------------------------
Visualizes the Campus Graph and Grid Maps using Matplotlib and custom layout styling.

Features:
- Two-floor campus layout with clear floor distinction and stairwell connector.
- Room type color coding (Classrooms, Labs, Offices, Library, Corridors, Amenities).
- Highlighting for:
  * Current / Start position (cyan ring with glow)
  * Visited / Planned path (vibrant gold line with arrows)
  * Candidate locations with probability tags (orange markers)
  * Recovered item location (emerald green marker with star)
  * Blocked edges (red dashed lines with 'X')
  * Nodes explored during search (lavender highlight)
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from environment.graph import CampusGraph
from environment.grid import GridMap


# Color theme for campus locations
TYPE_COLORS = {
    "corridor":  "#8995A1",
    "classroom": "#2D668D",
    "lab":       "#70539B",
    "library":   "#B07828",
    "office":    "#337A62",
    "canteen":   "#B35E35",
    "washroom":  "#7B8794",
    "parking":   "#276B72",
}

# Coordinate offsets for 2D visualization of the 20 campus nodes
# Ground floor on left/bottom, First floor on right/top for optimal clarity
CAMPUS_VIS_COORDS: dict[str, tuple[float, float]] = {
    # --- Ground Floor ---
    "Main Entrance": (1.0, 1.0),
    "Reception":     (3.0, 1.0),
    "Canteen":       (5.0, 1.0),
    "Washroom-G":    (7.0, 1.0),
    "Corridor-G1":   (1.0, 2.5),
    "Corridor-G2":   (3.0, 2.5),
    "Corridor-G3":   (5.0, 2.5),
    "Library":       (1.0, 4.0),
    "Lab-A":         (3.0, 4.0),
    "Lab-B":         (5.0, 4.0),
    "Parking":       (7.0, 2.5),
    # --- Inter-floor connector ---
    "Stairwell":     (2.0, 5.5),
    # --- First Floor ---
    "Corridor-F1":   (4.0, 5.5),
    "Corridor-F2":   (6.0, 5.5),
    "Classroom-101": (2.0, 7.0),
    "Classroom-102": (4.0, 7.0),
    "Classroom-103": (6.0, 7.0),
    "Office-A":      (2.0, 8.5),
    "Office-B":      (4.0, 8.5),
    "Washroom-F":    (6.0, 8.5),
}


def draw_campus_map(
    graph: CampusGraph,
    start_node: Optional[str] = None,
    path: Optional[Sequence[str]] = None,
    candidate_nodes: Optional[Sequence[str]] = None,
    candidate_probs: Optional[dict[str, float]] = None,
    recovered_node: Optional[str] = None,
    explored_nodes: Optional[Sequence[str]] = None,
    blocked_edges: Optional[Sequence[tuple[str, str]]] = None,
    last_known_node: Optional[str] = None,
    visited_nodes: Optional[Sequence[str]] = None,
    figsize: tuple[float, float] = (11, 7.5),
) -> plt.Figure:
    """
    Renders an academic-grade architectural campus map visualization.
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor="#F7F8F5")
    ax.set_facecolor("#F7F8F5")

    # Draw Floor Background Panels
    ground_rect = mpatches.FancyBboxPatch(
        (0.2, 0.4), 7.6, 4.2, boxstyle="round,pad=0.16",
        ec="#D5DED8", fc="#FFFFFF", alpha=1, lw=1.0
    )
    ax.add_patch(ground_rect)
    ax.text(0.55, 4.28, "GROUND FLOOR", color="#54616E", fontsize=9, fontweight="bold")

    first_rect = mpatches.FancyBboxPatch(
        (1.2, 4.9), 5.6, 4.2, boxstyle="round,pad=0.16",
        ec="#D5DED8", fc="#FFFFFF", alpha=1, lw=1.0
    )
    ax.add_patch(first_rect)
    ax.text(1.55, 8.78, "FIRST FLOOR", color="#54616E", fontsize=9, fontweight="bold")
    ax.text(0.25, 9.48, "CAMPUS SEARCH MAP", color="#173F5F", fontsize=14, fontweight="bold", va="top")
    ax.text(0.25, 9.16, "Simulated navigation layout · corridor values represent movement cost", color="#667381", fontsize=8.5, va="top")

    # Convert path and explored to convenient lookups
    path_list = list(path) if path else []
    path_edges: set[tuple[str, str]] = set()
    for i in range(len(path_list) - 1):
        u, v = path_list[i], path_list[i + 1]
        path_edges.add((u, v))
        path_edges.add((v, u))

    blocked_set: set[tuple[str, str]] = set()
    if blocked_edges:
        for u, v in blocked_edges:
            blocked_set.add((u, v))
            blocked_set.add((v, u))

    cand_set = set(candidate_nodes) if candidate_nodes else set()
    expl_set = set(explored_nodes) if explored_nodes else set()
    visited_set = set(visited_nodes) if visited_nodes else set()
    probs = candidate_probs or {}

    # 1. Draw Normal Edges
    for edge in graph.all_edges():
        u, v, weight = edge.source, edge.target, edge.weight
        if (u, v) in blocked_set or (v, u) in blocked_set:
            continue  # drawn in blocked pass

        pos_u = CAMPUS_VIS_COORDS.get(u, (0, 0))
        pos_v = CAMPUS_VIS_COORDS.get(v, (0, 0))

        is_path_edge = (u, v) in path_edges

        if not is_path_edge:
            ax.plot(
                [pos_u[0], pos_v[0]], [pos_u[1], pos_v[1]],
                color="#B8C7BC", lw=1.8, alpha=0.9, zorder=1
            )

    # 2. Draw Blocked Edges
    if blocked_edges:
        for u, v in blocked_edges:
            if u in CAMPUS_VIS_COORDS and v in CAMPUS_VIS_COORDS:
                pos_u = CAMPUS_VIS_COORDS[u]
                pos_v = CAMPUS_VIS_COORDS[v]
                ax.plot(
                    [pos_u[0], pos_v[0]], [pos_u[1], pos_v[1]],
                    color="#C24135", lw=3.0, ls=":", alpha=0.9, zorder=3
                )
                mid_x = (pos_u[0] + pos_v[0]) / 2
                mid_y = (pos_u[1] + pos_v[1]) / 2
                ax.text(
                    mid_x, mid_y, "CLOSED",
                    color="#9B2C22", fontsize=7, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.18", fc="#FDECE9", ec="none"),
                    zorder=4
                )

    # 3. Draw Explored Nodes (Frontier expansions)
    for name in expl_set:
        if name in CAMPUS_VIS_COORDS and name != start_node and name != recovered_node:
            x, y = CAMPUS_VIS_COORDS[name]
            ax.scatter(
                [x], [y], s=620, color="#CFC6DF", alpha=0.45,
                edgecolors="none", linewidths=0, zorder=5
            )

    for name in visited_set:
        if name in CAMPUS_VIS_COORDS and name not in {start_node, recovered_node}:
            x, y = CAMPUS_VIS_COORDS[name]
            ax.scatter(
                [x], [y], s=520, facecolors="none", edgecolors="#176B62",
                linewidths=1.8, zorder=5
            )

    # 4. Draw Path with Arrows
    if len(path_list) >= 2:
        for i in range(len(path_list) - 1):
            u, v = path_list[i], path_list[i + 1]
            pos_u = CAMPUS_VIS_COORDS[u]
            pos_v = CAMPUS_VIS_COORDS[v]
            ax.annotate(
                "", xy=(pos_v[0], pos_v[1]), xytext=(pos_u[0], pos_u[1]),
                arrowprops=dict(
                        arrowstyle="->,head_width=0.3,head_length=0.4",
                        color="#C77732", lw=3.0, alpha=0.95
                ),
                zorder=6
            )

    # 5. Draw All Campus Nodes
    for node in graph.all_nodes():
        name = node.name
        if name not in CAMPUS_VIS_COORDS:
            continue
        x, y = CAMPUS_VIS_COORDS[name]

        node_color = TYPE_COLORS.get(node.node_type, "#718096")
        edge_color = "#FFFFFF"
        lw = 1.4
        size = 360

        # Highlighting rules
        if name == start_node:
            node_color = "#238B77"
            edge_color = "#126B5D"
            lw = 3.5
            size = 570
        elif name == recovered_node:
            node_color = "#27845B"
            edge_color = "#1B6847"
            lw = 4.0
            size = 600
        elif name == last_known_node:
            node_color = "#7955AA"
            edge_color = "#5B3D89"
            lw = 3.0
            size = 520
        elif name in cand_set:
            node_color = "#D8832D"
            edge_color = "#A95D19"
            lw = 2.5
            size = 480

        ax.scatter([x], [y], s=size, color=node_color, edgecolors=edge_color, linewidths=lw, zorder=7)

        # Node Name Label
        display_name = name.replace("-", " ")
        if name == start_node:
            display_name = f"{name}\nCURRENT"
        elif name == recovered_node:
            display_name = f"{name}\nRECOVERED"
        elif name == last_known_node:
            display_name = f"{name}\nLAST SEEN"
        elif name in cand_set:
            prob = probs.get(name, 0.5)
            display_name = f"{name}\nP = {prob:.2f}"
        elif name in visited_set:
            display_name = f"{name}\nVISITED"

        ax.text(
            x, y - 0.3, display_name,
            color="#263B33", fontsize=7.5, fontweight="bold", ha="center", va="top",
            zorder=8
        )

    # Formatting
    ax.set_xlim(-0.3, 8.5)
    ax.set_ylim(-0.2, 9.72)
    ax.axis("off")
    legend_handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=8,
               markerfacecolor="#238B77", markeredgecolor="#126B5D", label="Current position"),
        Line2D([], [], marker="D", linestyle="none", markersize=7,
               markerfacecolor="#7955AA", markeredgecolor="#5B3D89", label="Last seen"),
        Line2D([], [], marker="o", linestyle="none", markersize=8,
               markerfacecolor="#D8832D", markeredgecolor="#A95D19", label="Candidate"),
        Line2D([], [], marker="o", linestyle="--", color="#18786D",
               markerfacecolor="none", markeredgecolor="#18786D", label="Visited"),
        Line2D([], [], color="#C18A2C", linewidth=3, label="Planned route"),
        Line2D([], [], color="#C24135", linewidth=2, linestyle=":", label="Blocked corridor"),
        Line2D([], [], marker="*", linestyle="none", markersize=10,
               markerfacecolor="#27845B", markeredgecolor="#1B6847", label="Recovered (simulation)"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=4,
        frameon=False,
        fontsize=8,
        handletextpad=0.5,
        columnspacing=1.0,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return fig


def draw_grid_map(
    grid: GridMap,
    start_pos: Optional[str] = None,
    path: Optional[Sequence[str]] = None,
    candidate_pos: Optional[Sequence[str]] = None,
    goal_pos: Optional[str] = None,
    recovered_pos: Optional[str] = None,
    explored_cells: Optional[Sequence[str]] = None,
    figsize: tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Renders an academic visualization of a 2D grid search environment.
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor="#FFFFFF")
    ax.set_facecolor("#FBFCFA")

    # Create grid display matrix: 0=free, 1=obstacle, 2=explored, 3=path,
    # 4=candidate, 5=start, 6=goal, 7=recovered.
    matrix = np.zeros((grid.rows, grid.cols), dtype=int)

    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.is_obstacle(r, c):
                matrix[r, c] = 1

    if explored_cells:
        for name in explored_cells:
            try:
                r, c = grid.name_to_pos(name)
                if matrix[r, c] == 0:
                    matrix[r, c] = 2
            except (ValueError, IndexError):
                pass

    if path:
        for name in path:
            try:
                r, c = grid.name_to_pos(name)
                matrix[r, c] = 3
            except (ValueError, IndexError):
                pass

    if candidate_pos:
        for name in candidate_pos:
            try:
                r, c = grid.name_to_pos(name)
                matrix[r, c] = 4
            except (ValueError, IndexError):
                pass

    if start_pos:
        try:
            r, c = grid.name_to_pos(start_pos)
            matrix[r, c] = 5
        except (ValueError, IndexError):
            pass

    if goal_pos:
        try:
            r, c = grid.name_to_pos(goal_pos)
            matrix[r, c] = 8 if goal_pos == start_pos else 6
        except (ValueError, IndexError):
            pass

    if recovered_pos:
        try:
            r, c = grid.name_to_pos(recovered_pos)
            matrix[r, c] = 7
        except (ValueError, IndexError):
            pass

    # Custom colormap
    from matplotlib.colors import ListedColormap
    # 0: free, 1: obstacle, 2: explored, 3: path, 4: candidate,
    # 5: start, 6: goal, 7: recovered, 8: coincident start and goal.
    cmap = ListedColormap([
        "#EEF3EF",  # Free
        "#34473E",  # Obstacle
        "#C9BCE4",  # Explored
        "#E9B95E",  # Path
        "#E89A4D",  # Candidate
        "#3A9C84",  # Start
        "#3478A8",  # Goal
        "#27845B",  # Recovered
        "#165E6C",  # Start and goal
    ])

    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=8, origin="upper")

    if grid.rows <= 20 and grid.cols <= 20:
        marker_fontsize = 8 if max(grid.rows, grid.cols) <= 12 else 6
        cell_labels = {
            1: ("#", "#FFFFFF"),
            2: ("·", "#62428A"),
            3: ("●", "#5B4212"),
            4: ("C", "#63340D"),
            5: ("S", "#FFFFFF"),
            6: ("G", "#FFFFFF"),
            7: ("R", "#FFFFFF"),
            8: ("S/G", "#FFFFFF"),
        }
        for (row, col), code in np.ndenumerate(matrix):
            if int(code) in cell_labels:
                label, label_color = cell_labels[int(code)]
                ax.text(
                    col,
                    row,
                    label,
                    ha="center",
                    va="center",
                    color=label_color,
                    fontsize=marker_fontsize,
                    fontweight="bold",
                )

    # Add grid lines
    ax.set_xticks(np.arange(-0.5, grid.cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid.rows, 1), minor=True)
    ax.grid(which="minor", color="#FFFFFF", linestyle="-", linewidth=1.4)
    ax.tick_params(which="minor", size=0)

    ax.set_xticks(range(0, grid.cols, max(1, grid.cols // 10)))
    ax.set_yticks(range(0, grid.rows, max(1, grid.rows // 10)))
    ax.tick_params(colors="#64766C", labelsize=8)
    ax.set_xlabel("Column", color="#52665B", fontsize=9)
    ax.set_ylabel("Row", color="#52665B", fontsize=9)

    ax.set_title(
        f"Grid Map ({grid.rows}×{grid.cols}) — Obstacles: "
        f"{grid.obstacle_count} ({grid.obstacle_count/(grid.rows*grid.cols):.1%})",
        color="#263B33", fontsize=11, fontweight="bold", pad=12
    )

    legend_entries = [
        mpatches.Patch(facecolor="#EEF3EF", edgecolor="#B8C7BC", label="Free"),
        mpatches.Patch(facecolor="#34473E", edgecolor="#34473E", label="Obstacle (#)"),
        mpatches.Patch(facecolor="#C9BCE4", edgecolor="#8D75B8", label="Explored (·)"),
        mpatches.Patch(facecolor="#E9B95E", edgecolor="#C18A2C", label="Path (●)"),
    ]
    if candidate_pos:
        legend_entries.append(
            mpatches.Patch(facecolor="#E89A4D", edgecolor="#A95D19", label="Candidate (C)")
        )
    if goal_pos == start_pos and goal_pos is not None:
        legend_entries.append(
            mpatches.Patch(facecolor="#165E6C", edgecolor="#165E6C", label="Start & goal (S/G)")
        )
    else:
        legend_entries.extend([
            mpatches.Patch(facecolor="#3A9C84", edgecolor="#126B5D", label="Start (S)"),
            mpatches.Patch(facecolor="#3478A8", edgecolor="#245A80", label="Goal (G)"),
        ])
    if recovered_pos:
        legend_entries.append(
            mpatches.Patch(facecolor="#27845B", edgecolor="#1B6847", label="Recovered")
        )
    fig.legend(
        handles=legend_entries,
        loc="lower center",
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return fig
