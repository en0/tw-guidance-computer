"""Port for bulk intel export/import operations."""

from typing import Protocol

from tw_guidance_computer.domain.models import (
    Planet,
    Port,
    Sector,
    WarpConnection,
)


class IntelStore(Protocol):
    """Bulk export/import port for intel sync.

    Export methods return only locally-discovered records (source IS NULL).
    Import methods accept records with timestamps and apply merge strategies:
    - Sectors: explored beats unexplored; ties keep local.
    - Ports: freshest updated_at wins (strict >); ties keep local.
    - Warps: replace-per-sector-if-newer (grouped by from_sector).
    - Planets: additive (INSERT OR IGNORE).

    All methods raise StorageError on failure.
    """

    def get_local_sectors(self) -> list[tuple[Sector, float]]:
        """Return all locally-discovered sectors with their updated_at timestamps.

        Returns:
            List of (Sector, updated_at) tuples where source IS NULL.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_local_ports(self) -> list[tuple[Port, float]]:
        """Return all locally-discovered ports with their updated_at timestamps.

        Returns:
            List of (Port, updated_at) tuples where source IS NULL.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_local_warps(self) -> list[tuple[WarpConnection, float]]:
        """Return all locally-discovered warps with their updated_at timestamps.

        Returns:
            List of (WarpConnection, updated_at) tuples where source IS NULL.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def get_local_planets(self) -> list[tuple[Planet, float]]:
        """Return all locally-discovered planets with their updated_at timestamps.

        Returns:
            List of (Planet, updated_at) tuples where source IS NULL.

        Raises:
            StorageError: If the read fails.
        """
        ...

    def import_sectors(self, sectors: list[tuple[Sector, float]], source: str) -> int:
        """Import sectors from a remote source.

        Merge strategy: explored beats unexplored. If both have the same
        explored status, the local record is kept (strict > for freshness).

        Args:
            sectors: List of (Sector, updated_at) tuples to import.
            source: The keyhash identifying the remote source.

        Returns:
            Number of records inserted or updated.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def import_ports(self, ports: list[tuple[Port, float]], source: str) -> int:
        """Import ports from a remote source.

        Merge strategy: freshest updated_at wins (strict >). Ties keep local.

        Args:
            ports: List of (Port, updated_at) tuples to import.
            source: The keyhash identifying the remote source.

        Returns:
            Number of records inserted or updated.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def import_warps(self, warps: list[tuple[WarpConnection, float]], source: str) -> int:
        """Import warps from a remote source.

        Merge strategy: replace-per-sector-if-newer. Incoming warps are grouped
        by from_sector. For each sector group, if the imported timestamp is
        strictly greater than the max local updated_at for that sector's warps,
        all local warps from that sector are deleted and replaced with the
        imported set. If local is newer or equal, the sector group is skipped.

        Args:
            warps: List of (WarpConnection, updated_at) tuples to import.
            source: The keyhash identifying the remote source.

        Returns:
            Number of records inserted.

        Raises:
            StorageError: If the write fails.
        """
        ...

    def import_planets(self, planets: list[tuple[Planet, float]], source: str) -> int:
        """Import planets from a remote source.

        Merge strategy: additive (INSERT OR IGNORE).

        Args:
            planets: List of (Planet, updated_at) tuples to import.
            source: The keyhash identifying the remote source.

        Returns:
            Number of records inserted.

        Raises:
            StorageError: If the write fails.
        """
        ...
