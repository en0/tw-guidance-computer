"""Use case: render sector art for a given sector."""

from __future__ import annotations

import random
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.sector_art import compose_scene


@final
class RenderSectorArt:
    """Orchestrate store queries and domain art generation for a sector.

    Queries the store for port name, planet presence, and stardock
    (port_class == 0), then delegates to domain art generation.
    """

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, sector_id: int, width: int, height: int) -> list[list[tuple[str, str]]]:
        """Render the sector art grid.

        Args:
            sector_id: The sector to render.
            width: Canvas width in characters.
            height: Canvas height in rows.

        Returns:
            Grid of (character, ansi_color_escape) tuples.
        """
        port = self._store.get_port(sector_id)
        port_name = port.name if port else None
        has_stardock = port is not None and port.port_class == 0
        has_planet = self._store.has_planet(sector_id)
        seed = random.randint(0, 2**32)

        return compose_scene(
            width=width,
            height=height,
            port_name=port_name,
            has_planet=has_planet,
            has_stardock=has_stardock,
            seed=seed,
        )
