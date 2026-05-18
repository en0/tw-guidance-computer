"""Use case: find ports within N hops of a sector."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import NearbyPort


@final
class FindNearbyPorts:
    """BFS to find all ports within a given hop distance."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, sector_id: int, max_hops: int = 5) -> list[NearbyPort]:
        """Find ports reachable within max_hops.

        Args:
            sector_id: Starting sector.
            max_hops: Maximum search distance.

        Returns:
            List of NearbyPort sorted by distance.
        """
        warps = self._store.get_all_warps()
        adj: dict[int, set[int]] = defaultdict(set)
        for w in warps:
            adj[w.from_sector].add(w.to_sector)
            adj[w.to_sector].add(w.from_sector)

        queue: deque[tuple[int, int]] = deque([(sector_id, 0)])
        visited = {sector_id: 0}
        while queue:
            current, dist = queue.popleft()
            if dist >= max_hops:
                continue
            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))

        results: list[NearbyPort] = []
        for sid, hops in visited.items():
            if hops > 0:
                port = self._store.get_port(sid)
                if port:
                    results.append(NearbyPort(hops=hops, port=port))

        results.sort(key=lambda x: x.hops)
        return results
