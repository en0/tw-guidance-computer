"""Use case: get recent chat messages."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import ChatMessage


@final
class GetRecentChat:
    """Retrieve recent chat messages."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, limit: int = 30) -> list[ChatMessage]:
        """Get recent chat messages.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            Most recent chat messages, newest first.
        """
        return self._store.get_recent_chat(limit)
