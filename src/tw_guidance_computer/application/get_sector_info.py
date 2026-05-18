"""Use case: get detailed sector information."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import SectorDetail


@final
class GetSectorInfo:
    """Retrieve full detail for a sector including warps and port."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, sector_id: int) -> SectorDetail | None:
        """Get sector detail including warps and port info.

        Args:
            sector_id: The sector to look up.

        Returns:
            Full sector detail, or None if the sector is unknown.
        """
        sector = self._store.get_sector(sector_id)
        if sector is None:
            return None

        warps = self._store.get_warps(sector_id)
        port = self._store.get_port(sector_id)

        warp_ports = {}
        for w in warps:
            wp = self._store.get_port(w.to_sector)
            if wp is not None:
                warp_ports[w.to_sector] = wp

        return SectorDetail(
            sector=sector,
            warps=warps,
            port=port,
            warp_ports=warp_ports,
        )
