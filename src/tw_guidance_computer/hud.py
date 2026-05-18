"""Entry point for the TW Guidance Computer HUD service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tw_guidance_computer.adapters.inbound.tui import HudDisplay
from tw_guidance_computer.compose import AppContext

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tw-guidance-computer" / "game.db"


def main() -> None:
    """Start the TW2002 Guidance Computer HUD."""
    parser = argparse.ArgumentParser(description="TW2002 Guidance Computer — real-time HUD")
    parser.add_argument("logfile", type=Path, help="Path to the script session log file")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--parse-existing",
        action="store_true",
        help="Parse the entire existing log before starting the HUD",
    )
    args = parser.parse_args()

    if not args.logfile.exists():
        print(f"Error: log file not found: {args.logfile}", file=sys.stderr)
        sys.exit(1)

    ctx = AppContext(db_path=args.db, log_path=args.logfile)
    assert ctx.reader is not None

    # Optionally parse existing log content first
    if args.parse_existing:
        full_text = ctx.reader.read_full()
        ctx.use_cases.parse_log_chunk.execute(full_text)

    hud = HudDisplay(reader=ctx.reader, use_cases=ctx.use_cases)

    try:
        hud.run()
    finally:
        ctx.close()
