"""Entry point for the TW Guidance Computer HUD service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tw_guidance_computer.adapters.inbound.tui import HudDisplay
from tw_guidance_computer.compose import AppContext, build_profile_use_cases, resolve_db_path
from tw_guidance_computer.domain.exceptions import (
    ConfigError,
    GuidanceError,
    ProfileExistsError,
    ProfileNotFoundError,
)


def main() -> None:
    """Start the TW2002 Guidance Computer HUD."""
    parser = argparse.ArgumentParser(description="TW2002 Guidance Computer — real-time HUD")
    parser.add_argument("logfile", type=Path, help="Path to the script session log file")
    parser.add_argument(
        "-p", "--profile", type=str, default=None,
        help="Profile to use (default: configured default)",
    )
    parser.add_argument(
        "--create", action="store_true",
        help="Create the profile if it doesn't exist",
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

    if args.create and args.profile:
        _, create_profile, _ = build_profile_use_cases()
        try:
            profile = create_profile.execute(args.profile)
            print(f"Note: Created profile '{profile.name}' (db: {profile.db_path})", file=sys.stderr)
        except ProfileExistsError:
            pass  # Already exists, continue normally
        except GuidanceError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        db_path = resolve_db_path(args.profile)
    except (ConfigError, ProfileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    ctx = AppContext(db_path=db_path, log_path=args.logfile)
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
