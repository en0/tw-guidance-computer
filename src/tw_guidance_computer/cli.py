"""Entry point for the TW Guidance Computer CLI query tool."""

from __future__ import annotations

import sys

from tw_guidance_computer.compose import build_cli
from tw_guidance_computer.domain.exceptions import GuidanceError


def main() -> None:
    """TW2002 Guidance Computer CLI — query the game knowledge base."""
    try:
        build_cli().run()
    except GuidanceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
