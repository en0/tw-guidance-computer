"""Domain service: graph operations on the warp network."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from tw_guidance_computer.domain.models.sector import WarpConnection


@dataclass(frozen=True)
class WarpGraph:
    """Bidirectional warp graph with BFS operations.

    Constructed from a list of WarpConnections. All edges are treated as
    bidirectional regardless of the from/to direction in the source data.
    """

    warps: list[WarpConnection]
    _adj: dict[int, set[int]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Build adjacency dict from warp connections."""
        adj: dict[int, set[int]] = {}
        for w in self.warps:
            adj.setdefault(w.from_sector, set()).add(w.to_sector)
            adj.setdefault(w.to_sector, set()).add(w.from_sector)
        object.__setattr__(self, "_adj", adj)

    def neighbors(self, sector_id: int) -> set[int]:
        """Return sectors directly reachable from sector_id.

        Args:
            sector_id: The sector to query.

        Returns:
            Set of adjacent sector IDs, empty if sector unknown.
        """
        return self._adj.get(sector_id, set())

    def bfs_path(self, start: int, end: int) -> list[int] | None:
        """Find shortest path between two sectors.

        Args:
            start: Starting sector ID.
            end: Destination sector ID.

        Returns:
            Ordered list of sector IDs from start to end inclusive, or None
            if no path exists.
        """
        if start == end:
            return [start]

        queue: deque[tuple[int, list[int]]] = deque([(start, [start])])
        visited = {start}

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adj.get(current, set()):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def bfs_distances(self, start: int, max_hops: int | None = None) -> dict[int, int]:
        """Compute distances from start to all reachable sectors.

        Args:
            start: Starting sector ID.
            max_hops: Maximum distance to search. None for unbounded.

        Returns:
            Dict mapping sector_id to hop distance (excludes start itself).
        """
        queue: deque[tuple[int, int]] = deque([(start, 0)])
        visited: dict[int, int] = {start: 0}

        while queue:
            current, dist = queue.popleft()
            if max_hops is not None and dist >= max_hops:
                continue
            for neighbor in self._adj.get(current, set()):
                if neighbor not in visited:
                    visited[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))

        del visited[start]
        return visited

    def bfs_first_match(self, start: int, targets: set[int]) -> tuple[int, list[int]] | None:
        """Find the nearest target sector and the path to it.

        Args:
            start: Starting sector ID.
            targets: Set of sector IDs to search for.

        Returns:
            Tuple of (target_sector_id, path) for the nearest target,
            or None if no target is reachable.
        """
        if start in targets:
            return (start, [start])

        queue: deque[tuple[int, list[int]]] = deque([(start, [start])])
        visited = {start}

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adj.get(current, set()):
                if neighbor in targets:
                    return (neighbor, path + [neighbor])
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None
