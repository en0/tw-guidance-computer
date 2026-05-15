"""Use case: find trade pairs from known port data."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import CommodityType, TradePair


@final
class FindTradePairs:
    """Find adjacent ports with complementary buy/sell patterns."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, min_complementary: int = 2) -> list[TradePair]:
        """Find all trade pairs with at least N complementary commodities.

        Args:
            min_complementary: Minimum number of complementary commodities.

        Returns:
            Trade pairs sorted by complementary count descending.
        """
        ports = {p.sector_id: p for p in self._store.get_all_ports()}
        warps = self._store.get_all_warps()

        # Build adjacency
        adjacency: dict[int, set[int]] = {}
        for w in warps:
            adjacency.setdefault(w.from_sector, set()).add(w.to_sector)

        pairs: list[TradePair] = []
        seen: set[tuple[int, int]] = set()

        for sector_a, neighbors in adjacency.items():
            if sector_a not in ports:
                continue
            port_a = ports[sector_a]
            if len(port_a.port_type) != 3 or port_a.port_type == "Special":
                continue

            for sector_b in neighbors:
                if sector_b not in ports:
                    continue
                key = (min(sector_a, sector_b), max(sector_a, sector_b))
                if key in seen:
                    continue
                seen.add(key)

                port_b = ports[sector_b]
                if len(port_b.port_type) != 3 or port_b.port_type == "Special":
                    continue

                commodities = [CommodityType.FUEL_ORE, CommodityType.ORGANICS, CommodityType.EQUIPMENT]
                complements = 0
                routes: list[str] = []

                for i, c in enumerate(commodities):
                    a_dir = port_a.port_type[i]
                    b_dir = port_b.port_type[i]
                    if a_dir == "S" and b_dir == "B":
                        complements += 1
                        routes.append(f"buy {c.value} at [{sector_a}], sell at [{sector_b}]")
                    elif a_dir == "B" and b_dir == "S":
                        complements += 1
                        routes.append(f"buy {c.value} at [{sector_b}], sell at [{sector_a}]")

                if complements >= min_complementary:
                    pairs.append(
                        TradePair(
                            sector_a=sector_a,
                            sector_b=sector_b,
                            port_a_name=port_a.name,
                            port_b_name=port_b.name,
                            port_a_type=port_a.port_type,
                            port_b_type=port_b.port_type,
                            complementary_count=complements,
                            routes=routes,
                        )
                    )

        pairs.sort(key=lambda p: p.complementary_count, reverse=True)
        return pairs
