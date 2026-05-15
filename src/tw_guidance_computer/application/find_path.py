"""Use case: find shortest path between two sectors."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.exceptions import PathNotFoundError


@final
class FindPath:
    """BFS shortest path between two sectors using known warps."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, start: int, end: int) -> list[int]:
        """Find the shortest known path between two sectors.

        Args:
            start: Starting sector ID.
            end: Destination sector ID.

        Returns:
            Ordered list of sector IDs from start to end inclusive.

        Raises:
            PathNotFoundError: If no path exists in the known warp graph.
        """
        if start == end:
            return [start]

        warps = self._store.get_all_warps()
        adj: dict[int, set[int]] = defaultdict(set)
        for w in warps:
            adj[w.from_sector].add(w.to_sector)
            adj[w.to_sector].add(w.from_sector)

        queue: deque[tuple[int, list[int]]] = deque([(start, [start])])
        visited = {start}

        while queue:
            current, path = queue.popleft()
            for neighbor in adj[current]:
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        raise PathNotFoundError(f"No known path from {start} to {end}")
