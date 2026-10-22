"""
environment/graph.py
--------------------
CampusGraph — a weighted, undirected graph of named campus locations.

Design decisions
~~~~~~~~~~~~~~~~
* Adjacency is stored as ``dict[str, dict[str, Edge]]`` so that
  ``get_neighbors`` is O(degree) — appropriate for sparse campus maps.
* Edges are stored in both directions internally.  ``all_edges`` deduplicates.
* ``block_edge`` / ``unblock_edge`` allow dynamic obstacle simulation without
  removing the edge from the adjacency structure.
"""

from __future__ import annotations

from environment.models import Edge, Node


class CampusGraph:
    """
    Weighted, undirected graph representing campus locations.

    Nodes are keyed by their unique ``name`` string.
    Edges carry a ``weight`` (travel cost) and a ``blocked`` flag.
    """

    def __init__(self) -> None:
        # name → Node
        self._nodes: dict[str, Node] = {}
        # name → list of (neighbor_name, weight, blocked)
        # stored as {source: {target: Edge}}  for O(1) lookup
        self._edges: dict[str, dict[str, Edge]] = {}

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> None:
        """Register a node.  Silently replaces if name already exists."""
        self._nodes[node.name] = node
        if node.name not in self._edges:
            self._edges[node.name] = {}

    def get_node(self, name: str) -> Node:
        """Return a Node by name.  Raises KeyError if not found."""
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' does not exist in graph.")
        return self._nodes[name]

    def has_node(self, name: str) -> bool:
        return name in self._nodes

    def all_nodes(self) -> list[Node]:
        """Return all nodes in insertion order."""
        return list(self._nodes.values())

    def node_names(self) -> list[str]:
        return list(self._nodes.keys())

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def add_edge(
        self,
        source: str,
        target: str,
        weight: float = 1.0,
        blocked: bool = False,
    ) -> None:
        """
        Add an undirected edge between *source* and *target*.

        Both nodes must already be registered via ``add_node``.
        Calling this again with the same (source, target) pair updates the
        weight and blocked flag.
        """
        for name in (source, target):
            if name not in self._nodes:
                raise KeyError(f"Node '{name}' not found.  Add it first.")

        edge_fwd = Edge(source=source, target=target, weight=weight, blocked=blocked)
        edge_bwd = Edge(source=target, target=source, weight=weight, blocked=blocked)

        self._edges[source][target] = edge_fwd
        self._edges[target][source] = edge_bwd

    def remove_edge(self, source: str, target: str) -> None:
        """Remove an edge in both directions.  No-op if edge does not exist."""
        self._edges.get(source, {}).pop(target, None)
        self._edges.get(target, {}).pop(source, None)

    def block_edge(self, source: str, target: str) -> None:
        """Mark an edge as impassable.  Raises KeyError if edge missing."""
        self._get_edge_pair(source, target)  # validates existence
        self._edges[source][target].blocked = True
        self._edges[target][source].blocked = True

    def unblock_edge(self, source: str, target: str) -> None:
        """Restore a blocked edge to passable."""
        self._get_edge_pair(source, target)
        self._edges[source][target].blocked = False
        self._edges[target][source].blocked = False

    def get_neighbors(self, name: str) -> list[tuple[str, float]]:
        """
        Return ``[(neighbor_name, edge_weight)]`` for all *unblocked* edges.

        Only traversable (non-blocked) neighbors are returned.
        The order is deterministic (insertion order in Python 3.7+).
        """
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' does not exist.")
        result = []
        for target, edge in self._edges[name].items():
            if not edge.blocked:
                result.append((target, edge.weight))
        return result

    def all_edges(self) -> list[Edge]:
        """
        Return all edges without duplicates (each undirected edge once).
        Canonical form: source < target alphabetically.
        """
        seen: set[frozenset[str]] = set()
        edges: list[Edge] = []
        for src, neighbors in self._edges.items():
            for tgt, edge in neighbors.items():
                key = frozenset({src, tgt})
                if key not in seen:
                    seen.add(key)
                    edges.append(edge)
        return edges

    def has_edge(self, source: str, target: str) -> bool:
        return target in self._edges.get(source, {})

    def edge_weight(self, source: str, target: str) -> float:
        """Return weight of edge.  Raises KeyError if edge missing."""
        try:
            return self._edges[source][target].weight
        except KeyError:
            raise KeyError(f"No edge between '{source}' and '{target}'.")

    # ------------------------------------------------------------------
    # Graph-level queries
    # ------------------------------------------------------------------

    def has_path(self, source: str, target: str) -> bool:
        """
        Return True if *target* is reachable from *source* via BFS
        using only unblocked edges.
        """
        if source not in self._nodes:
            raise KeyError(f"Node '{source}' does not exist in graph.")
        if target not in self._nodes:
            raise KeyError(f"Node '{target}' does not exist in graph.")
        if source == target:
            return True
        from collections import deque

        visited: set[str] = {source}
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            for neighbor, _ in self.get_neighbors(current):
                if neighbor == target:
                    return True
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def to_adjacency_dict(self) -> dict[str, list[tuple[str, float]]]:
        """
        Return a plain-Python adjacency dict (unblocked edges only).
        Useful for serialisation and debugging.
        """
        return {name: self.get_neighbors(name) for name in self._nodes}

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, name: str) -> bool:
        return name in self._nodes

    def __repr__(self) -> str:
        return (
            f"CampusGraph(nodes={len(self._nodes)}, "
            f"edges={len(self.all_edges())})"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_edge_pair(self, source: str, target: str) -> tuple[Edge, Edge]:
        """Return (fwd_edge, bwd_edge) or raise KeyError."""
        try:
            fwd = self._edges[source][target]
            bwd = self._edges[target][source]
        except KeyError:
            raise KeyError(f"Edge between '{source}' and '{target}' does not exist.")
        return fwd, bwd
