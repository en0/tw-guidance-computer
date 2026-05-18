"""Inbound CLI adapter — translates CLI commands into use case calls and formats output."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, final

from tw_guidance_computer.domain.exceptions import GuidanceError, PathNotFoundError

if TYPE_CHECKING:
    from tw_guidance_computer.application.use_cases import UseCases


@contextmanager
def _cli_boundary() -> Iterator[None]:
    """Catch domain exceptions and translate to CLI error output."""
    try:
        yield
    except GuidanceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


@final
class CliAdapter:
    """Handles CLI command dispatch and output formatting."""

    def __init__(self, use_cases: UseCases) -> None:
        """Initialize with use cases.

        Args:
            use_cases: Pre-wired use case container.
        """
        self._uc = use_cases

    def status(self) -> None:
        """Print database summary."""
        with _cli_boundary():
            summary = self._uc.get_database_summary.execute()
            status = self._uc.get_player_status.execute()

            seen = summary.sectors_total - summary.sectors_explored
            print(f"  Sectors known: {summary.sectors_total} ({summary.sectors_explored} explored, {seen} seen)")
            print(f"  Ports known: {summary.ports_total}")
            print(f"  Warp connections: {summary.warps_total}")

            if status:
                turns = status.turns_remaining
                print(f"  Player: sector {status.sector_id}, {turns} turns, {status.credits:,} credits")

            if summary.port_type_counts:
                print(f"  Port types: {summary.port_type_counts}")

    def sector(self, sector_id: int) -> None:
        """Print sector info."""
        with _cli_boundary():
            detail = self._uc.get_sector_info.execute(sector_id)
            if not detail:
                print(f"  Sector {sector_id}: No data")
                return

            print(f"  Sector {sector_id}: {detail.sector.region or 'Unknown'}")
            print(f"  Explored: {'Yes' if detail.sector.explored else 'No'}")

            if detail.warps:
                warp_strs = []
                for w in detail.warps:
                    port = detail.warp_ports.get(w.to_sector)
                    extra = f" [{port.port_type}]" if port else (" (?)" if not w.explored else "")
                    warp_strs.append(f"{w.to_sector}{extra}")
                print(f"  Warps: {', '.join(warp_strs)}")

            if detail.port:
                print(f"  Port: {detail.port.name} - Class {detail.port.port_class} ({detail.port.port_type})")
                for pc in detail.port.commodities:
                    print(f"    {pc.commodity.value:<10} {pc.direction.value:<8} {pc.quantity:>5} ({pc.pct}%)")

    def ports(self, type_filter: str | None = None) -> None:
        """Print all known ports."""
        with _cli_boundary():
            all_ports = self._uc.list_ports.execute(type_filter)

            for port in all_ports:
                items_str = ""
                if port.commodities:
                    parts = [f"{pc.commodity.value[0]}:{pc.direction.value[0]}{pc.quantity}" for pc in port.commodities]
                    items_str = " " + " ".join(parts)
                print(f"  {port.sector_id:>4}: {port.name:<20} Class {port.port_class} ({port.port_type}){items_str}")

    def pairs(self) -> None:
        """Print trade pairs."""
        with _cli_boundary():
            results = self._uc.find_trade_pairs.execute()
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
        with _cli_boundary():
            try:
                result = self._uc.find_path.execute(start, end)
                print(f"  Path ({len(result) - 1} hops): {' > '.join(str(s) for s in result)}")
                for s in result:
                    detail = self._uc.get_sector_info.execute(s)
                    if detail and detail.port:
                        print(f"    {s}: {detail.port.name} ({detail.port.port_type})")
            except PathNotFoundError as e:
                print(f"  {e}")

    def search(self, pattern: str) -> None:
        """Print ports matching a type pattern."""
        with _cli_boundary():
            results = self._uc.search_ports.execute(pattern)
            if not results:
                print(f"  No ports matching '{pattern}'")
                return

            print(f"  Ports matching '{pattern}':")
            for port in results:
                detail = self._uc.get_sector_info.execute(port.sector_id)
                region = detail.sector.region if detail else ""
                print(f"    {port.sector_id:>4}: {port.name:<20} ({port.port_type}) - {region}")

    def nearby(self, sector_id: int, max_hops: int) -> None:
        """Print ports near a sector."""
        with _cli_boundary():
            results = self._uc.find_nearby_ports.execute(sector_id, max_hops)
            if not results:
                print(f"  No ports within {max_hops} hops of sector {sector_id}")
                return

            print(f"  Ports within {max_hops} hops of sector {sector_id}:")
            for nearby in results:
                print(
                    f"    {nearby.hops} hops - [{nearby.port.sector_id}] {nearby.port.name} ({nearby.port.port_type})"
                )

    def sell(self, max_hops: int) -> None:
        """Print sell recommendations."""
        with _cli_boundary():
            status = self._uc.get_player_status.execute()
            if not status:
                print("  No player status available.")
                return
            if not status.cargo:
                print("  Not carrying anything.")
                return

            carrying = [h.commodity for h in status.cargo]
            recs = self._uc.find_sell_locations.execute(status.sector_id, carrying, max_hops)

            if not recs:
                print(f"  No known buyers within {max_hops} hops.")
                return

            print(f"  Sell recommendations from sector {status.sector_id}:")
            for rec in recs[:10]:
                commodities = ", ".join(c.value for c in rec.commodities_accepted)
                print(f"    {rec.hops} hops - [{rec.sector_id}] {rec.port_name} buys: {commodities}")

    def chat(self) -> None:
        """Print recent chat messages."""
        with _cli_boundary():
            messages = self._uc.get_recent_chat.execute(limit=30)
            if not messages:
                print("  No chat messages.")
                return

            for msg in reversed(messages):
                print(f"  [{msg.channel}] {msg.sender}: {msg.message}")

    def nearest_pair(self, sector_id: int, limit: int = 5) -> None:
        """Print nearest trade pairs to a sector."""
        with _cli_boundary():
            results = self._uc.find_nearest_pair.execute(sector_id, limit)
            if not results:
                print(f"  No trade pairs reachable from sector {sector_id}")
                return

            print(f"  Nearest trade pairs to sector {sector_id}:")
            for nearest in results:
                p = nearest.pair
                line = (
                    f"[{p.sector_a}] ({p.port_a_type}) <-> [{p.sector_b}] ({p.port_b_type})"
                    f"  [{p.complementary_count}/3]"
                )
                print(f"\n    {nearest.hops} hops - {line}")
                for r in p.routes:
                    print(f"      {r}")

    def sector_art(self, sector_id: int) -> None:
        """Render sector art for a previously visited sector."""
        with _cli_boundary():
            grid = self._uc.render_sector_art.execute(sector_id, 80, 14)

            detail = self._uc.get_sector_info.execute(sector_id)
            region = detail.sector.region if detail else "Unknown"
            print(f"─── Sector {sector_id}: {region} ───")

            # Render with ANSI color
            reset = "\033[0m"
            for row in grid:
                parts = []
                for cell in row:
                    if cell.color:
                        parts.append(f"{cell.color}{cell.char}{reset}")
                    else:
                        parts.append(cell.char)
                print("".join(parts))
