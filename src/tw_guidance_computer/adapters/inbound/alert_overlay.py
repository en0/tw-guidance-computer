"""Pure helper for generating safe harbor alert overlay text."""

from __future__ import annotations

from tw_guidance_computer.domain.models import SafeHarborRoute


def format_alert_overlay(
    route: SafeHarborRoute | None, turns_remaining: int
) -> list[str]:
    """Generate overlay content lines for the safe harbor alert.

    Args:
        route: The safe harbor route result, or None if no route exists.
        turns_remaining: Current turn count.

    Returns:
        List of content lines (without border formatting).
    """
    lines = [f"TURNS CRITICAL: {turns_remaining} remaining", ""]

    if route is None:
        lines.append("Uhoh, I think you're in trouble.")
        lines.append("No known route to safe space.")
    elif route.hops == 0:
        lines.append("You are currently in a safe sector.")
        lines.append(f"({route.destination_name})")
    else:
        route_sectors = route.route
        if len(route_sectors) > 10:
            displayed = " → ".join(str(s) for s in route_sectors[:8])
            remaining = len(route_sectors) - 8
            route_str = f"{displayed} ... ({remaining} more)"
        else:
            route_str = " → ".join(str(s) for s in route_sectors)
        lines.append(f"Nearest safe harbor: Sector {route.destination_sector}")
        lines.append(f"Route: {route_str}")
        lines.append(f"Distance: {route.hops} hops")

    return lines
