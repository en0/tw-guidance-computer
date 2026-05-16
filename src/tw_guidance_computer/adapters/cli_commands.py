"""Inbound CLI adapter — translates CLI commands into use case calls and formats output."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.find_nearby_ports import FindNearbyPorts
from tw_guidance_computer.application.find_nearest_pair import FindNearestPair
from tw_guidance_computer.application.find_path import FindPath
from tw_guidance_computer.application.find_sell_locations import FindSellLocations
from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.application.search_ports import SearchPorts
from tw_guidance_computer.domain.exceptions import PathNotFoundError


@final
class CliAdapter:
    """Handles CLI command dispatch and output formatting."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def status(self) -> None:
        """Print database summary."""
        ports = self._store.get_all_ports()
        warps = self._store.get_all_warps()
        status = self._store.get_player_status()

        # Count sectors by querying all known (from warps + ports)
        sector_ids: set[int] = set()
        explored_ids: set[int] = set()
        for w in warps:
            sector_ids.add(w.from_sector)
            sector_ids.add(w.to_sector)
            if w.explored:
                explored_ids.add(w.to_sector)
            explored_ids.add(w.from_sector)
        for p in ports:
            sector_ids.add(p.sector_id)
            explored_ids.add(p.sector_id)

        # Get actual explored count from store
        explored = 0
        total = 0
        for sid in sector_ids:
            total += 1
            sector = self._store.get_sector(sid)
            if sector and sector.explored:
                explored += 1

        print(f"  Sectors known: {total} ({explored} explored, {total - explored} seen)")
        print(f"  Ports known: {len(ports)}")
        print(f"  Warp connections: {len(warps)}")

        if status:
            print(f"  Player: sector {status.sector_id}, {status.turns_remaining} turns, {status.credits:,} credits")

        # Port type breakdown
        types: dict[str, int] = {}
        for p in ports:
            types[p.port_type] = types.get(p.port_type, 0) + 1
        if types:
            print(f"  Port types: {dict(sorted(types.items()))}")

    def sector(self, sector_id: int) -> None:
        """Print sector info."""
        sector = self._store.get_sector(sector_id)
        if not sector:
            print(f"  Sector {sector_id}: No data")
            return

        print(f"  Sector {sector_id}: {sector.region or 'Unknown'}")
        print(f"  Explored: {'Yes' if sector.explored else 'No'}")

        warps = self._store.get_warps(sector_id)
        if warps:
            warp_strs = []
            for w in warps:
                port = self._store.get_port(w.to_sector)
                extra = f" [{port.port_type}]" if port else (" (?)" if not w.explored else "")
                warp_strs.append(f"{w.to_sector}{extra}")
            print(f"  Warps: {', '.join(warp_strs)}")

        port = self._store.get_port(sector_id)
        if port:
            print(f"  Port: {port.name} - Class {port.port_class} ({port.port_type})")
            for pc in port.commodities:
                print(f"    {pc.commodity.value:<10} {pc.direction.value:<8} {pc.quantity:>5} ({pc.pct}%)")

    def ports(self, type_filter: str | None = None) -> None:
        """Print all known ports."""
        all_ports = self._store.get_all_ports()
        all_ports.sort(key=lambda p: p.sector_id)

        for port in all_ports:
            if type_filter and port.port_type != type_filter.upper():
                continue
            items_str = ""
            if port.commodities:
                parts = [f"{pc.commodity.value[0]}:{pc.direction.value[0]}{pc.quantity}" for pc in port.commodities]
                items_str = " " + " ".join(parts)
            print(f"  {port.sector_id:>4}: {port.name:<20} Class {port.port_class} ({port.port_type}){items_str}")

    def pairs(self) -> None:
        """Print trade pairs."""
        results = FindTradePairs(self._store).execute()
        if not results:
            print("  No trade pairs found.")
            return

        for p in results:
            header = f"  [{p.sector_a}] {p.port_a_name} ({p.port_a_type})"
            header += f"  <-->  [{p.sector_b}] {p.port_b_name} ({p.port_b_type})"
            print(f"\n{header}")
            print(f"  Complementary: {p.complementary_count}/3")
            for r in p.routes:
                print(f"    {r}")

    def path(self, start: int, end: int) -> None:
        """Print shortest path."""
        try:
            result = FindPath(self._store).execute(start, end)
            print(f"  Path ({len(result) - 1} hops): {' > '.join(str(s) for s in result)}")
            for s in result:
                port = self._store.get_port(s)
                if port:
                    print(f"    {s}: {port.name} ({port.port_type})")
        except PathNotFoundError as e:
            print(f"  {e}")

    def search(self, pattern: str) -> None:
        """Print ports matching a type pattern."""
        results = SearchPorts(self._store).execute(pattern)
        if not results:
            print(f"  No ports matching '{pattern}'")
            return

        print(f"  Ports matching '{pattern}':")
        for port in results:
            sector = self._store.get_sector(port.sector_id)
            region = sector.region if sector else ""
            print(f"    {port.sector_id:>4}: {port.name:<20} ({port.port_type}) - {region}")

    def nearby(self, sector_id: int, max_hops: int) -> None:
        """Print ports near a sector."""
        results = FindNearbyPorts(self._store).execute(sector_id, max_hops)
        if not results:
            print(f"  No ports within {max_hops} hops of sector {sector_id}")
            return

        print(f"  Ports within {max_hops} hops of sector {sector_id}:")
        for hops, port in results:
            print(f"    {hops} hops - [{port.sector_id}] {port.name} ({port.port_type})")

    def sell(self, max_hops: int) -> None:
        """Print sell recommendations."""
        status = self._store.get_player_status()
        if not status:
            print("  No player status available.")
            return
        if not status.cargo:
            print("  Not carrying anything.")
            return

        carrying = [h.commodity for h in status.cargo]
        recs = FindSellLocations(self._store).execute(status.sector_id, carrying, max_hops)

        if not recs:
            print(f"  No known buyers within {max_hops} hops.")
            return

        print(f"  Sell recommendations from sector {status.sector_id}:")
        for rec in recs[:10]:
            commodities = ", ".join(c.value for c in rec.commodities_accepted)
            print(f"    {rec.hops} hops - [{rec.sector_id}] {rec.port_name} buys: {commodities}")

    def chat(self) -> None:
        """Print recent chat messages."""
        messages = self._store.get_recent_chat(limit=30)
        if not messages:
            print("  No chat messages.")
            return

        for msg in reversed(messages):
            print(f"  [{msg.channel}] {msg.sender}: {msg.message}")

    def nearest_pair(self, sector_id: int, limit: int = 5) -> None:
        """Print nearest trade pairs to a sector."""
        results = FindNearestPair(self._store).execute(sector_id, limit)
        if not results:
            print(f"  No trade pairs reachable from sector {sector_id}")
            return

        print(f"  Nearest trade pairs to sector {sector_id}:")
        for hops, p in results:
            line = f"[{p.sector_a}] ({p.port_a_type}) <-> [{p.sector_b}] ({p.port_b_type})  [{p.complementary_count}/3]"
            print(f"\n    {hops} hops - {line}")
            for r in p.routes:
                print(f"      {r}")
