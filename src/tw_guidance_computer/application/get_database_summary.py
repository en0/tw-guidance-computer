"""Use case: get database summary statistics."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import DatabaseSummary


@final
class GetDatabaseSummary:
    """Compute aggregate statistics about the game knowledge base."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self) -> DatabaseSummary:
        """Compute database summary.

        Returns:
            Aggregate statistics about known game state.
        """
        ports = self._store.get_all_ports()
        warps = self._store.get_all_warps()

        sector_ids: set[int] = set()
        for w in warps:
            sector_ids.add(w.from_sector)
            sector_ids.add(w.to_sector)
        for p in ports:
            sector_ids.add(p.sector_id)

        explored = 0
        for sid in sector_ids:
            sector = self._store.get_sector(sid)
            if sector and sector.explored:
                explored += 1

        type_counts: dict[str, int] = {}
        for p in ports:
            type_counts[p.port_type] = type_counts.get(p.port_type, 0) + 1

        return DatabaseSummary(
            sectors_total=len(sector_ids),
            sectors_explored=explored,
            ports_total=len(ports),
            warps_total=len(warps),
            port_type_counts=dict(sorted(type_counts.items())),
        )
