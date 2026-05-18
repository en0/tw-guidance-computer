"""Entry point for the TW Guidance Computer CLI query tool."""

from __future__ import annotations

import argparse
import sys

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.compose import AppContext, resolve_db_path
from tw_guidance_computer.domain.exceptions import ConfigError, GuidanceError, ProfileNotFoundError


def _handle_profile_command(args: argparse.Namespace) -> None:
    """Handle profile subcommands."""
    from tw_guidance_computer.compose import build_profile_use_cases

    _, create_uc, list_uc = build_profile_use_cases()

    match args.profile_command:
        case "create":
            profile = create_uc.execute(args.name)
            print(f"Created profile '{profile.name}' (db: {profile.db_path})")
        case "list":
            listing = list_uc.execute()
            for p in listing.profiles:
                marker = "  * " if p.name == listing.default_name else "    "
                suffix = " (default)" if p.name == listing.default_name else ""
                print(f"{marker}{p.name}{suffix}")
        case _:
            print("Usage: tw profile {create|list}", file=sys.stderr)
            sys.exit(1)


def main() -> None:
    """TW2002 Guidance Computer CLI — query the game knowledge base."""
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

    profile_parser = sub.add_parser("profile", help="Manage profiles")
    profile_sub = profile_parser.add_subparsers(dest="profile_command")
    p = profile_sub.add_parser("create", help="Create a new profile")
    p.add_argument("name")
    profile_sub.add_parser("list", help="List all profiles")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "profile":
        try:
            _handle_profile_command(args)
        except GuidanceError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    try:
        db_path = resolve_db_path(args.profile)
    except (ConfigError, ProfileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not db_path.exists():
        print(f"No database found at {db_path}. Run tw-hud first to populate it.", file=sys.stderr)
        sys.exit(1)

    ctx = AppContext(db_path=db_path)
    cli = CliAdapter(ctx.use_cases)

    try:
        match args.command:
            case "status":
                cli.status()
            case "sector":
                cli.sector(args.sector)
            case "ports":
                cli.ports(args.type)
            case "pairs":
                cli.pairs()
            case "path":
                cli.path(args.start, args.end)
            case "search":
                cli.search(args.pattern)
            case "nearby":
                cli.nearby(args.sector, args.hops)
            case "nearest-pair":
                cli.nearest_pair(args.sector, args.limit)
            case "sell":
                cli.sell(args.hops)
            case "chat":
                cli.chat()
            case "sector-art":
                cli.sector_art(args.sector)
    finally:
        ctx.close()
