"""Port for persistent game state storage."""

from typing import Protocol

from tw_guidance_computer.domain.models import (
    ChatMessage,
    Planet,
    PlayerStatus,
    Port,
    Sector,
    TradePair,
    WarpConnection,
)


class GameStateStore(Protocol):
    """Persistent storage for all game knowledge.

    Implementations must be safe for concurrent read access (CLI queries
    while the HUD service is writing).
    """

    def upsert_sector(self, sector: Sector) -> None:
        """Insert or update a sector.

        Args:
            sector: The sector to store.
        """
        ...

    def upsert_port(self, port: Port) -> None:
        """Insert or update a port.

        Args:
            port: The port to store.
        """
        ...

    def upsert_warp(self, warp: WarpConnection) -> None:
        """Insert or update a warp connection.

        Args:
            warp: The warp connection to store.
        """
        ...

    def set_player_status(self, status: PlayerStatus) -> None:
        """Update the current player status.

        Args:
            status: The current player state.
        """
        ...

    def add_chat_message(self, message: ChatMessage) -> None:
        """Append a chat message to the log.

        Args:
            message: The chat message to store.
        """
        ...

    def get_sector(self, sector_id: int) -> Sector | None:
        """Retrieve a sector by ID.

        Args:
            sector_id: The sector number.

        Returns:
            The sector if known, None otherwise.
        """
        ...

    def get_port(self, sector_id: int) -> Port | None:
        """Retrieve a port by its sector ID.

        Args:
            sector_id: The sector containing the port.

        Returns:
            The port if known, None otherwise.
        """
        ...

    def get_warps(self, sector_id: int) -> list[WarpConnection]:
        """Get all warp connections from a sector.

        Args:
            sector_id: The source sector.

        Returns:
            List of warp connections from this sector.
        """
        ...

    def get_all_warps(self) -> list[WarpConnection]:
        """Get all known warp connections.

        Returns:
            Every warp connection in the database.
        """
        ...

    def get_all_ports(self) -> list[Port]:
        """Get all known ports.

        Returns:
            Every port in the database.
        """
        ...

    def get_player_status(self) -> PlayerStatus | None:
        """Get the current player status.

        Returns:
            The last known player state, or None if never set.
        """
        ...

    def get_recent_chat(self, limit: int = 20) -> list[ChatMessage]:
        """Get recent chat messages.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            Most recent chat messages, newest first.
        """
        ...

    def get_trade_pairs(self) -> list[TradePair]:
        """Compute and return all known adjacent trade pairs.

        Returns:
            Trade pairs sorted by complementary count descending.
        """
        ...

    def upsert_planet(self, planet: Planet) -> None:
        """Insert or update a planet.

        Args:
            planet: The planet to store.
        """
        ...

    def has_planet(self, sector_id: int) -> bool:
        """Check if a sector has at least one planet.

        Args:
            sector_id: The sector to check.

        Returns:
            True if the sector has a planet, False otherwise.
        """
        ...
