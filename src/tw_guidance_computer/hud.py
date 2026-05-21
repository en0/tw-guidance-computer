"""Entry point for the TW Guidance Computer HUD service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tw_guidance_computer.adapters.inbound.tui import HudDisplay
from tw_guidance_computer.compose import AppContext, build_profile_use_cases
from tw_guidance_computer.domain.exceptions import GuidanceError, ProfileExistsError


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

    # Pre-flight: create profile if requested (before main app construction)
    if args.create and args.profile:
        create_profile, _ = build_profile_use_cases()
        try:
            profile = create_profile.execute(args.profile)
            print(f"Note: Created profile '{profile.name}' (db: {profile.db_path})", file=sys.stderr)
        except ProfileExistsError:
            pass
        except GuidanceError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        ctx = AppContext(profile_name=args.profile, log_path=args.logfile)
    except GuidanceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    assert ctx.reader is not None

    if args.parse_existing:
        full_text = ctx.reader.read_full()
        ctx.use_cases.parse_log_chunk.execute(full_text)

    hud = HudDisplay(reader=ctx.reader, use_cases=ctx.use_cases, turn_thresholds=ctx.thresholds)

    try:
        hud.run()
    finally:
        ctx.close()
