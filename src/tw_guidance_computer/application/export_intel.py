"""Use case: export local intel data to CSV string."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.intel_store import IntelStore
from tw_guidance_computer.domain.intel_csv import serialize_intel


@final
class ExportIntel:
    """Export all locally-discovered intel as a CSV string."""

    def __init__(self, store: IntelStore) -> None:
        """Initialize with an intel store.

        Args:
            store: The intel store for reading local data.
        """
        self._store = store

    def execute(self) -> str:
        """Read all local data and serialize to CSV.

        Returns:
            CSV string with all local sectors, ports, warps, and planets.

        Raises:
            IntelDataError: If serialization fails.
        """
        sectors = self._store.get_local_sectors()
        ports = self._store.get_local_ports()
        warps = self._store.get_local_warps()
        planets = self._store.get_local_planets()
        return serialize_intel(sectors, ports, warps, planets)
