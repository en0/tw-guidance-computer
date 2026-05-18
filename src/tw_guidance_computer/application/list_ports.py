"""Use case: list known ports with optional type filter."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import Port


@final
class ListPorts:
    """List all known ports, optionally filtered by type."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, type_filter: str | None = None) -> list[Port]:
        """Get all ports, optionally filtered by type code.

        Args:
            type_filter: If provided, only return ports matching this type (e.g., 'SSB').

        Returns:
            Ports sorted by sector ID.
        """
        ports = self._store.get_all_ports()
        if type_filter:
            ports = [p for p in ports if p.port_type == type_filter.upper()]
        ports.sort(key=lambda p: p.sector_id)
        return ports
