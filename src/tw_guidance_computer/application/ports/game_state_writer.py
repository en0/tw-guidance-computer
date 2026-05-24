"""Port for writing game state to persistent storage."""

from typing import Protocol

from tw_guidance_computer.domain.models import (
    ChatMessage,
    Planet,
    PlayerStatus,
    Port,
    Sector,
    WarpConnection,
)


class GameStateWriter(Protocol):
    """Write-side port for persistent game state storage.

    Used by the parser to persist extracted game data.
    Implementations must be safe for concurrent access.
    """

    def upsert_sector(self, sector: Sector) -> None:
        """Insert or update a sector.

        Args:
            sector: The sector to store.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def upsert_port(self, port: Port) -> None:
        """Insert or update a port.

        Args:
            port: The port to store.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def upsert_warp(self, warp: WarpConnection) -> None:
        """Insert or update a warp connection.

        Args:
            warp: The warp connection to store.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def set_player_status(self, status: PlayerStatus) -> None:
        """Update the current player status.

        Args:
            status: The current player state.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def add_chat_message(self, message: ChatMessage) -> None:
        """Append a chat message to the log.

        Args:
            message: The chat message to store.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def upsert_planet(self, planet: Planet) -> None:
        """Insert or update a planet.

        Args:
            planet: The planet to store.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def replace_warps_from_sector(self, sector_id: int, warps: list[WarpConnection]) -> None:
        """Delete all warps from a sector and insert the provided set.

        Self-healing semantics: the provided warp list is treated as the
        complete, authoritative set of warps from this sector. Any previously
        stored warps (including intel-imported ones) are removed and replaced.

        Args:
            sector_id: The sector whose outbound warps are being replaced.
            warps: The complete set of outbound warp connections from this sector.

        Raises:
            StorageError: If the write fails.
        """
        ...
