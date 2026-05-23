"""Use case: pull intel from the shared server."""

from __future__ import annotations

import time
from typing import final

from tw_guidance_computer.application.import_intel import ImportIntel
from tw_guidance_computer.application.ports.intel_transport import IntelTransport
from tw_guidance_computer.domain.exceptions import IntelDataError
from tw_guidance_computer.domain.models import IntelMergeResult


@final
class PullIntel:
    """Download and import intel from all remote sources."""

    def __init__(
        self,
        import_intel: ImportIntel,
        transport: IntelTransport,
        identity: str,
        max_file_size: int,
    ) -> None:
        """Initialize with import use case, transport, identity, and size limit.

        Args:
            import_intel: Use case for importing CSV intel data.
            transport: Transport port for downloading from the server.
            identity: SHA-256 hex hash identifying this player (excluded from pull).
            max_file_size: Maximum file size in bytes to download.
        """
        self._import_intel = import_intel
        self._transport = transport
        self._identity = identity
        self._max_file_size = max_file_size

    def execute(self, budget_seconds: float | None = None, offset: int = 0) -> IntelMergeResult:
        """Download and import intel from all remote sources.

        Args:
            budget_seconds: Optional time budget. Stops pulling new files when expired.
            offset: Starting index into the file list for rotating sync.

        Returns:
            Aggregate merge statistics across all sources.
        """
        deadline = time.monotonic() + budget_seconds if budget_seconds is not None else None
        files = [f for f in self._transport.list_files() if f.name != self._identity]
        if not files:
            return IntelMergeResult()

        total_sectors = 0
        total_ports = 0
        total_ports_updated = 0
        total_warps = 0
        total_planets = 0

        start = offset % len(files)
        ordered = files[start:] + files[:start]

        for remote_file in ordered:
            if deadline is not None and time.monotonic() >= deadline:
                break
            if remote_file.size > self._max_file_size:
                continue
            try:
                content = self._transport.download(remote_file.name)
                result = self._import_intel.execute(content, remote_file.name)
                total_sectors += result.sectors_added
                total_ports += result.ports_added
                total_ports_updated += result.ports_updated
                total_warps += result.warps_added
                total_planets += result.planets_added
            except IntelDataError:
                continue

        return IntelMergeResult(
            sectors_added=total_sectors,
            ports_added=total_ports,
            ports_updated=total_ports_updated,
            warps_added=total_warps,
            planets_added=total_planets,
        )
