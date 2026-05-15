"""Use case: find the best place to sell current cargo."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import CommodityType, Port, SellRecommendation, TradeDirection


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

        warps = self._store.get_all_warps()
        adj: dict[int, set[int]] = defaultdict(set)
        for w in warps:
            adj[w.from_sector].add(w.to_sector)
            adj[w.to_sector].add(w.from_sector)

        ports = {p.sector_id: p for p in self._store.get_all_ports()}

        # BFS from current sector
        queue: deque[tuple[int, int]] = deque([(from_sector, 0)])
        visited = {from_sector}
        results: list[SellRecommendation] = []

        while queue:
            current, dist = queue.popleft()
            if dist > max_hops:
                break

            if current in ports and dist > 0:
                port = ports[current]
                accepted = _port_buys(port, carrying)
                if accepted:
                    results.append(
                        SellRecommendation(
                            sector_id=current,
                            port_name=port.name,
                            hops=dist,
                            commodities_accepted=accepted,
                        )
                    )

            for neighbor in adj[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return results


def _port_buys(port: Port, carrying: list[CommodityType]) -> list[CommodityType]:
    """Determine which carried commodities this port will buy."""
    buying: set[CommodityType] = set()

    # Check from port_type code
    commodity_order = [CommodityType.FUEL_ORE, CommodityType.ORGANICS, CommodityType.EQUIPMENT]
    if len(port.port_type) == 3:
        for i, c in enumerate(commodity_order):
            if port.port_type[i] == "B":
                buying.add(c)

    # Also check detailed commodities if available
    for pc in port.commodities:
        if pc.direction == TradeDirection.BUYING:
            buying.add(pc.commodity)

    return [c for c in carrying if c in buying]
