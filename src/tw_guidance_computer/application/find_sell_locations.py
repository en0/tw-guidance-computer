"""Use case: find the best place to sell current cargo."""

from __future__ import annotations

from collections import deque
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import CommodityType, SellRecommendation
from tw_guidance_computer.domain.warp_graph import WarpGraph


@final
class FindSellLocations:
    """Find the nearest ports that buy what the player is carrying."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, from_sector: int, carrying: list[CommodityType], max_hops: int = 10) -> list[SellRecommendation]:
        """Find nearest ports that buy the player's cargo.

        Args:
            from_sector: Current sector ID.
            carrying: List of commodity types the player is carrying.
            max_hops: Maximum search distance.

        Returns:
            Sell recommendations sorted by hops ascending.
        """
        if not carrying:
            return []

        graph = WarpGraph(self._store.get_all_warps())
        ports = {p.sector_id: p for p in self._store.get_all_ports()}

        queue: deque[tuple[int, int]] = deque([(from_sector, 0)])
        visited = {from_sector}
        results: list[SellRecommendation] = []

        while queue:
            current, dist = queue.popleft()
            if dist > max_hops:
                break

            if current in ports and dist > 0:
                port = ports[current]
                accepted = [c for c in carrying if c in port.buying_commodities]
                if accepted:
                    results.append(
                        SellRecommendation(
                            sector_id=current,
                            port_name=port.name,
                            hops=dist,
                            commodities_accepted=accepted,
                        )
                    )

            for neighbor in graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return results
