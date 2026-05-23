"""Pure helper for generating shutdown sync modal content."""

from __future__ import annotations


def format_sync_modal(status: str | None) -> list[str]:
    """Generate content lines for the shutdown sync modal.

    Args:
        status: Current shutdown status string, or None if not shutting down.

    Returns:
        List of content lines (without border formatting). Empty if status is None.
    """
    if status is None:
        return []
    return [status]
