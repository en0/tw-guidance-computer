"""Entry point for the TW Guidance Computer HUD service."""

from __future__ import annotations

import sys

from tw_guidance_computer.compose import build_hud
from tw_guidance_computer.domain.exceptions import GuidanceError


def main() -> None:
    """Start the TW2002 Guidance Computer HUD."""
    try:
        build_hud().run()
    except GuidanceError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
