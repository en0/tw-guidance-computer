"""Use case: search ports by type pattern."""

from __future__ import annotations

import re
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import Port


@final
class SearchPorts:
    """Search ports by type pattern with wildcard support."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, pattern: str) -> list[Port]:
        """Find ports matching a type pattern.

        Args:
            pattern: Type pattern (e.g., 'SSB', 'B*B'). * matches any single char.

        Returns:
            Matching ports sorted by sector ID.
        """
        regex = pattern.upper().replace("*", ".")
        ports = self._store.get_all_ports()
        results = [p for p in ports if re.fullmatch(regex, p.port_type)]
        results.sort(key=lambda p: p.sector_id)
        return results
