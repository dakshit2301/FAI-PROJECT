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
import numpy as np

from environment.graph import CampusGraph
from environment.grid import GridMap


# Color theme for campus locations
TYPE_COLORS = {
    "corridor":  "#64766C",
    "classroom": "#3478A8",
    "lab":       "#7651A8",
    "library":   "#B87916",
    "office":    "#27845B",
    "canteen":   "#C4642A",
    "washroom":  "#718096",
    "parking":   "#18786D",
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
    fig, ax = plt.subplots(figsize=figsize, facecolor="#FFFFFF")
    ax.set_facecolor("#FBFCFA")

    # Draw Floor Background Panels
    ground_rect = mpatches.FancyBboxPatch(
        (0.2, 0.4), 7.6, 4.2, boxstyle="round,pad=0.2",
        ec="#D7E2DA", fc="#F2F6F2", alpha=0.95, lw=1.2, ls="--"
    )
    ax.add_patch(ground_rect)
    ax.text(0.5, 4.4, "GROUND FLOOR", color="#718078", fontsize=10, fontweight="bold")

    first_rect = mpatches.FancyBboxPatch(
        (1.2, 4.9), 5.6, 4.2, boxstyle="round,pad=0.2",
        ec="#D7E2DA", fc="#F2F6F2", alpha=0.95, lw=1.2, ls="--"
    )
    ax.add_patch(first_rect)
    ax.text(1.5, 8.9, "FIRST FLOOR", color="#718078", fontsize=10, fontweight="bold")

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
            # Edge weight label
            mid_x = (pos_u[0] + pos_v[0]) / 2
            mid_y = (pos_u[1] + pos_v[1]) / 2
            ax.text(
                mid_x, mid_y, f"{weight:.1f}",
                color="#64766C", fontsize=7, ha="center", va="center",
                bbox=dict(boxstyle="circle,pad=0.1", fc="#FFFFFF", ec="none", alpha=0.9),
                zorder=2
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
                    mid_x, mid_y, "[X] BLOCKED",
                    color="#9B2C22", fontsize=8, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="#FEE9E6", ec="#E5A39B", lw=1),
                    zorder=4
                )

    # 3. Draw Explored Nodes (Frontier expansions)
    for name in expl_set:
        if name in CAMPUS_VIS_COORDS and name != start_node and name != recovered_node:
            x, y = CAMPUS_VIS_COORDS[name]
            ax.scatter(
                [x], [y], s=750, color="#B6A4D8", alpha=0.25,
                edgecolors="#8D75B8", linewidths=1.5, zorder=5
            )

    for name in visited_set:
        if name in CAMPUS_VIS_COORDS and name not in {start_node, recovered_node}:
            x, y = CAMPUS_VIS_COORDS[name]
            ax.scatter(
                [x], [y], s=950, facecolors="none", edgecolors="#4FD1C5",
                linewidths=2.0, linestyle="--", zorder=5
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
                        arrowstyle="->,head_width=0.4,head_length=0.6",
                        color="#C18A2C", lw=3.5, alpha=0.95
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
        lw = 1.5
        size = 550

        # Highlighting rules
        if name == start_node:
            node_color = "#238B77"
            edge_color = "#126B5D"
            lw = 3.5
            size = 850
        elif name == recovered_node:
            node_color = "#27845B"
            edge_color = "#1B6847"
            lw = 4.0
            size = 900
        elif name == last_known_node:
            node_color = "#7955AA"
            edge_color = "#5B3D89"
            lw = 3.0
            size = 750
        elif name in cand_set:
            node_color = "#D8832D"
            edge_color = "#A95D19"
            lw = 2.5
            size = 700

        ax.scatter([x], [y], s=size, color=node_color, edgecolors=edge_color, linewidths=lw, zorder=7)

        # Node Name Label
        display_name = name.replace("-", " ")
        if name == start_node:
            display_name = f"{name}\n[START]"
        elif name == recovered_node:
            display_name = f"{name}\n[RECOVERED]"
        elif name == last_known_node:
            display_name = f"{name}\n[LAST SEEN]"
        elif name in cand_set:
            prob = probs.get(name, 0.5)
            display_name = f"{name}\n(p={prob:.2f})"
        elif name in visited_set:
            display_name = f"{name}\n[VISITED]"

        ax.text(
            x, y - 0.38, display_name,
            color="#263B33", fontsize=8.5, fontweight="bold", ha="center", va="top",
            zorder=8
        )

    # Formatting
    ax.set_xlim(-0.3, 8.5)
    ax.set_ylim(-0.2, 9.6)
    ax.axis("off")
    fig.tight_layout()
    return fig


def draw_grid_map(
    grid: GridMap,
    start_pos: Optional[str] = None,
    path: Optional[Sequence[str]] = None,
    candidate_pos: Optional[Sequence[str]] = None,
    recovered_pos: Optional[str] = None,
    explored_cells: Optional[Sequence[str]] = None,
    figsize: tuple[float, float] = (8, 8),
) -> plt.Figure:
    """
    Renders an academic visualization of a 2D grid search environment.
    """
    fig, ax = plt.subplots(figsize=figsize, facecolor="#FFFFFF")
    ax.set_facecolor("#FBFCFA")

    # Create grid display matrix: 0=free, 1=obstacle, 2=explored, 3=path, 4=candidate, 5=start, 6=recovered
    matrix = np.zeros((grid.rows, grid.cols))

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

    if recovered_pos:
        try:
            r, c = grid.name_to_pos(recovered_pos)
            matrix[r, c] = 6
        except (ValueError, IndexError):
            pass

    # Custom colormap
    from matplotlib.colors import ListedColormap
    # 0: free, 1: obstacle, 2: explored, 3: path, 4: candidate, 5: start, 6: recovered
    cmap = ListedColormap([
        "#EEF3EF",  # Free
        "#34473E",  # Obstacle
        "#C9BCE4",  # Explored
        "#E9B95E",  # Path
        "#E89A4D",  # Candidate
        "#3A9C84",  # Start
        "#27845B",  # Recovered
    ])

    im = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=6, origin="upper")

    # Add grid lines
    ax.set_xticks(np.arange(-0.5, grid.cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid.rows, 1), minor=True)
    ax.grid(which="minor", color="#FFFFFF", linestyle="-", linewidth=1.4)
    ax.tick_params(which="minor", size=0)

    ax.set_xticks(range(0, grid.cols, max(1, grid.cols // 10)))
    ax.set_yticks(range(0, grid.rows, max(1, grid.rows // 10)))
    ax.tick_params(colors="#64766C", labelsize=8)

    ax.set_title(
        f"Grid Map ({grid.rows}×{grid.cols}) — Obstacles: {grid.obstacle_count} ({grid.obstacle_count/(grid.rows*grid.cols):.1%})",
        color="#263B33", fontsize=11, fontweight="bold", pad=12
    )

    fig.tight_layout()
    return fig
