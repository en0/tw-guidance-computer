"""Use case: find trade pairs from known port data."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.domain.models import TradePair, TradeRoute
from tw_guidance_computer.domain.warp_graph import WarpGraph


@final
class FindTradePairs:
    """Find adjacent ports with complementary buy/sell patterns."""

    def __init__(self, store: GameStateReader) -> None:
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
        graph = WarpGraph(self._store.get_all_warps())

        pairs: list[TradePair] = []
        seen: set[tuple[int, int]] = set()

        for sector_a in ports:
            port_a = ports[sector_a]
            if len(port_a.port_type) != 3 or port_a.port_type == "Special":
                continue

            for sector_b in graph.neighbors(sector_a):
                if sector_b not in ports:
                    continue
                key = (min(sector_a, sector_b), max(sector_a, sector_b))
                if key in seen:
                    continue
                seen.add(key)

                port_b = ports[sector_b]
                if len(port_b.port_type) != 3 or port_b.port_type == "Special":
                    continue

                trades = port_a.complementary_trades(port_b)
                if len(trades) >= min_complementary:
                    routes = [
                        TradeRoute(commodity=c, buy_sector=buy, sell_sector=sell)
                        for c, buy, sell in trades
                    ]
                    pairs.append(
                        TradePair(
                            sector_a=sector_a,
                            sector_b=sector_b,
                            port_a_name=port_a.name,
                            port_b_name=port_b.name,
                            port_a_type=port_a.port_type,
                            port_b_type=port_b.port_type,
                            complementary_count=len(trades),
                            routes=routes,
                        )
                    )

        pairs.sort(key=lambda p: p.complementary_count, reverse=True)
        return pairs
