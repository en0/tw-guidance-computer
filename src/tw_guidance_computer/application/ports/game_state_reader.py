"""Port for reading game state from persistent storage."""

from typing import Protocol

from tw_guidance_computer.domain.models import (
    ChatMessage,
    PlayerStatus,
    Port,
    Sector,
    WarpConnection,
)


class GameStateReader(Protocol):
    """Read-side port for persistent game state storage.

    Used by query use cases to retrieve game knowledge.
    Implementations must be safe for concurrent read access.
    """

    def get_sector(self, sector_id: int) -> Sector | None:
        """Retrieve a sector by ID.

        Args:
            sector_id: The sector number.

        Returns:
            The sector if known, None otherwise.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_port(self, sector_id: int) -> Port | None:
        """Retrieve a port by its sector ID.

        Args:
            sector_id: The sector containing the port.

        Returns:
            The port if known, None otherwise.

        Raises:
            StorageError: If the read fails or stored data is corrupt.
        """
        ...

    def get_warps(self, sector_id: int) -> list[WarpConnection]:
        """Get all warp connections from a sector.

        Args:
            sector_id: The source sector.

        Returns:
            List of warp connections from this sector.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_all_warps(self) -> list[WarpConnection]:
        """Get all known warp connections.

        Returns:
            Every warp connection in the database.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_all_ports(self) -> list[Port]:
        """Get all known ports.

        Returns:
            Every port in the database.

        Raises:
            StorageError: If the read fails or stored data is corrupt.
        """
        ...

    def get_player_status(self) -> PlayerStatus | None:
        """Get the current player status.

        Returns:
            The last known player state, or None if never set.

        Raises:
            StorageError: If the read fails or stored data is corrupt.
        """
        ...

    def get_recent_chat(self, limit: int = 20) -> list[ChatMessage]:
        """Get recent chat messages.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            Most recent chat messages, newest first.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def has_planet(self, sector_id: int) -> bool:
        """Check if a sector has at least one planet.

        Args:
            sector_id: The sector to check.

        Returns:
            True if the sector has a planet, False otherwise.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_safe_sector_ids(self) -> list[int]:
        """Get sector IDs that are safe destinations.

        Returns sectors in Federation space (region == 'The Federation')
        and sectors containing StarDock (port_class == 0).

        Returns:
            List of unique sector IDs considered safe.

        Raises:
            StorageError: If the read fails.
        """
        ...
