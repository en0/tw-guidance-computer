"""Use case: find the nearest trade pair to a given sector."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import final

from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import TradePair


@final
class FindNearestPair:
    """Find trade pairs sorted by distance from a given sector."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, sector_id: int, limit: int = 5) -> list[tuple[int, TradePair]]:
        """Find nearest trade pairs to a sector.

        Args:
            sector_id: Starting sector.
            limit: Maximum number of pairs to return.

        Returns:
            List of (hops_to_nearest_port, TradePair) sorted by distance.
        """
        pairs = FindTradePairs(self._store).execute()
        if not pairs:
            return []

        # BFS from sector_id to find distance to all reachable sectors
        warps = self._store.get_all_warps()
        adj: dict[int, set[int]] = defaultdict(set)
        for w in warps:
            adj[w.from_sector].add(w.to_sector)
            adj[w.to_sector].add(w.from_sector)

        queue: deque[tuple[int, int]] = deque([(sector_id, 0)])
        dist: dict[int, int] = {sector_id: 0}
        while queue:
            current, d = queue.popleft()
            for neighbor in adj[current]:
                if neighbor not in dist:
                    dist[neighbor] = d + 1
                    queue.append((neighbor, d + 1))

        # Score each pair by distance to the closer port
        scored: list[tuple[int, TradePair]] = []
        for pair in pairs:
            d_a = dist.get(pair.sector_a)
            d_b = dist.get(pair.sector_b)
            if d_a is None and d_b is None:
                continue
            min_dist = min(d for d in (d_a, d_b) if d is not None)
            scored.append((min_dist, pair))

        scored.sort(key=lambda x: x[0])
        return scored[:limit]
