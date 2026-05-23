"""Use case: import intel data from CSV string into local store."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.intel_store import IntelStore
from tw_guidance_computer.domain.intel_csv import deserialize_intel
from tw_guidance_computer.domain.models import IntelMergeResult


@final
class ImportIntel:
    """Import intel from a CSV string into the local store."""

    def __init__(self, store: IntelStore) -> None:
        """Initialize with an intel store.

        Args:
            store: The intel store for importing data.
        """
        self._store = store

    def execute(self, content: str, source: str) -> IntelMergeResult:
        """Deserialize CSV content and import into the store.

        Args:
            content: CSV string with intel data.
            source: Keyhash identifying the remote source.

        Returns:
            Merge statistics showing what was added/updated.

        Raises:
            IntelDataError: If the CSV content is corrupt or invalid.
        """
        sectors, ports, warps, planets = deserialize_intel(content)
        sectors_added = self._store.import_sectors(sectors, source)
        ports_added = self._store.import_ports(ports, source)
        warps_added = self._store.import_warps(warps, source)
        planets_added = self._store.import_planets(planets, source)
        return IntelMergeResult(
            sectors_added=sectors_added,
            ports_added=ports_added,
            warps_added=warps_added,
            planets_added=planets_added,
        )
