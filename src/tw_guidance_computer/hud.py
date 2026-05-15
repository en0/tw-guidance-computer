"""Composition root for the TW Guidance Computer HUD service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tw_guidance_computer.adapters.log_reader import TailLogReader
from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.adapters.tui import HudDisplay
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk

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

    # Ensure DB directory exists
    args.db.parent.mkdir(parents=True, exist_ok=True)

    store = SqliteGameStateStore(args.db)
    reader = TailLogReader(args.logfile)
    log_parser = ParseLogChunk(store)

    # Optionally parse existing log content first
    if args.parse_existing:
        full_text = reader.read_full()
        log_parser.execute(full_text)

    hud = HudDisplay(store=store, reader=reader, parser=log_parser)

    try:
        hud.run()
    finally:
        reader.close()
        store.close()
