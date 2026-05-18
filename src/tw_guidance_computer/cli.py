"""Entry point for the TW Guidance Computer CLI query tool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.compose import AppContext

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tw-guidance-computer" / "game.db"


def main() -> None:
    """TW2002 Guidance Computer CLI — query the game knowledge base."""
    parser = argparse.ArgumentParser(description="TW2002 Guidance Computer — query tool")
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {DEFAULT_DB_PATH})",
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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if not args.db.exists():
        print(f"No database found at {args.db}. Run tw-hud first to populate it.", file=sys.stderr)
        sys.exit(1)

    ctx = AppContext(db_path=args.db)
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
