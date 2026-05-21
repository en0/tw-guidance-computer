"""Inbound CLI adapter — translates CLI commands into use case calls and formats output."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, final

from tw_guidance_computer.domain.exceptions import GuidanceError, PathNotFoundError

if TYPE_CHECKING:
    from tw_guidance_computer.application.create_profile import CreateProfile
    from tw_guidance_computer.application.list_profiles import ListProfiles
    from tw_guidance_computer.application.use_cases import UseCases

GameContextFactory = Callable[[str | None], tuple["UseCases", Callable[[], None]]]


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

    def __init__(
        self,
        *,
        create_profile: CreateProfile,
        list_profiles: ListProfiles,
        game_context_factory: GameContextFactory,
    ) -> None:
        """Initialize with profile use cases and a game context factory.

        Args:
            create_profile: Use case for creating profiles.
            list_profiles: Use case for listing profiles.
            game_context_factory: Callable that takes a profile name and returns (UseCases, close_fn).
        """
        self._create_profile = create_profile
        self._list_profiles = list_profiles
        self._game_context_factory = game_context_factory
        self._uc: UseCases | None = None

    def run(self, argv: list[str] | None = None) -> None:
        """Parse arguments and dispatch to the appropriate handler.

        Args:
            argv: Command-line arguments (defaults to sys.argv[1:]).
        """
        parser = self._build_parser()
        args = parser.parse_args(argv)
        if not args.command:
            parser.print_help()
            sys.exit(0)

        with _cli_boundary():
            if args.command == "profile":
                self._dispatch_profile(args)
            else:
                self._dispatch_game(args)

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the full argparse parser with all subcommands."""
        parser = argparse.ArgumentParser(description="TW2002 Guidance Computer — query tool")
        parser.add_argument(
            "-p", "--profile", type=str, default=None,
            help="Profile to use (default: configured default)",
        )
        sub = parser.add_subparsers(dest="command")

        sub.add_parser("status", help="Database summary")

        p = sub.add_parser("sector", help="Show sector info")
        p.add_argument("sector", type=int)

        p = sub.add_parser("ports", help="List known ports")
        p.add_argument("-t", "--type", help="Filter by type (SSB, BBS, etc)")

        sub.add_parser("pairs", help="Find adjacent trade pairs")

        p = sub.add_parser("path", help="Find shortest path")
        p.add_argument("start", type=int)
        p.add_argument("end", type=int)

        p = sub.add_parser("search", help="Search ports by type (* = wildcard)")
        p.add_argument("pattern")

        p = sub.add_parser("nearby", help="Find ports near a sector")
        p.add_argument("sector", type=int)
        p.add_argument("-n", "--hops", type=int, default=5)

        p = sub.add_parser("nearest-pair", help="Find nearest trade pair to a sector")
        p.add_argument("sector", type=int)
        p.add_argument("-n", "--limit", type=int, default=5)

        p = sub.add_parser("sell", help="Find where to sell current cargo")
        p.add_argument("-n", "--hops", type=int, default=10)

        sub.add_parser("chat", help="Show recent chat messages")

        p = sub.add_parser("sector-art", help="View sector art for a visited sector")
        p.add_argument("sector", type=int)

        sub.add_parser("safe-harbor", help="Show nearest safe sector and route")

        profile_parser = sub.add_parser("profile", help="Manage profiles")
        profile_sub = profile_parser.add_subparsers(dest="profile_command")
        p = profile_sub.add_parser("create", help="Create a new profile")
        p.add_argument("name")
        profile_sub.add_parser("list", help="List all profiles")

        return parser

    def _dispatch_profile(self, args: argparse.Namespace) -> None:
        """Handle profile subcommands."""
        match args.profile_command:
            case "create":
                profile = self._create_profile.execute(args.name)
                print(f"Created profile '{profile.name}' (db: {profile.db_path})")
            case "list":
                listing = self._list_profiles.execute()
                for p in listing.profiles:
                    marker = "  * " if p.name == listing.default_name else "    "
                    suffix = " (default)" if p.name == listing.default_name else ""
                    print(f"{marker}{p.name}{suffix}")
            case _:
                print("Usage: tw profile {create|list}", file=sys.stderr)
                sys.exit(1)

    def _dispatch_game(self, args: argparse.Namespace) -> None:
        """Dispatch game commands using the context factory."""
        uc, close_fn = self._game_context_factory(args.profile)
        try:
            self._uc = uc
            match args.command:
                case "status":
                    self.status()
                case "sector":
                    self.sector(args.sector)
                case "ports":
                    self.ports(args.type)
                case "pairs":
                    self.pairs()
                case "path":
                    self.path(args.start, args.end)
                case "search":
                    self.search(args.pattern)
                case "nearby":
                    self.nearby(args.sector, args.hops)
                case "nearest-pair":
                    self.nearest_pair(args.sector, args.limit)
                case "sell":
                    self.sell(args.hops)
                case "chat":
                    self.chat()
                case "sector-art":
                    self.sector_art(args.sector)
                case "safe-harbor":
                    self.safe_harbor()
                case _:
                    print(f"Unknown command: {args.command}", file=sys.stderr)
                    sys.exit(1)
        finally:
            close_fn()

    def status(self) -> None:
        """Print database summary."""
        with _cli_boundary():
            assert self._uc is not None
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
            assert self._uc is not None
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
            assert self._uc is not None
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
            assert self._uc is not None
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
                    print(f"    buy {r.commodity.value} at [{r.buy_sector}], sell at [{r.sell_sector}]")

    def path(self, start: int, end: int) -> None:
        """Print shortest path."""
        with _cli_boundary():
            assert self._uc is not None
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
            assert self._uc is not None
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
            assert self._uc is not None
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
            assert self._uc is not None
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
            assert self._uc is not None
            messages = self._uc.get_recent_chat.execute(limit=30)
            if not messages:
                print("  No chat messages.")
                return

            for msg in reversed(messages):
                print(f"  [{msg.channel}] {msg.sender}: {msg.message}")

    def nearest_pair(self, sector_id: int, limit: int = 5) -> None:
        """Print nearest trade pairs to a sector."""
        with _cli_boundary():
            assert self._uc is not None
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
                    print(f"      buy {r.commodity.value} at [{r.buy_sector}], sell at [{r.sell_sector}]")

    def sector_art(self, sector_id: int) -> None:
        """Render sector art for a previously visited sector."""
        with _cli_boundary():
            assert self._uc is not None
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

    def safe_harbor(self) -> None:
        """Show nearest safe sector and route from current position."""
        with _cli_boundary():
            assert self._uc is not None
            status = self._uc.get_player_status.execute()
            if status is None:
                print("Error: No player position known. Play a session first.", file=sys.stderr)
                raise SystemExit(1)

            result = self._uc.find_safe_harbor.execute(status.sector_id)

            if result is None:
                print(f"No known route to safe space from sector {status.sector_id}.")
                print("Explore more sectors to find a path to The Federation or StarDock.")
            elif result.hops == 0:
                print(f"You are currently in a safe sector ({result.destination_name}).")
            else:
                route_str = " \u2192 ".join(str(s) for s in result.route)
                print(f"Safe harbor from sector {status.sector_id}:")
                print(f"  Nearest: Sector {result.destination_sector} ({result.destination_name})")
                print(f"  Route: {route_str} ({result.hops} hops)")
