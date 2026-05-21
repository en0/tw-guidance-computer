"""Use case: get current player status."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.domain.models import PlayerStatus


@final
class GetPlayerStatus:
    """Retrieve the current player status snapshot."""

    def __init__(self, store: GameStateReader) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self) -> PlayerStatus | None:
        """Get the current player status.

        Returns:
            The last known player state, or None if never set.
        """
        return self._store.get_player_status()
