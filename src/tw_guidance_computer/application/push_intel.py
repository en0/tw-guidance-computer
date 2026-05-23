"""Use case: push local intel to the shared server."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.export_intel import ExportIntel
from tw_guidance_computer.application.ports.intel_transport import IntelTransport


@final
class PushIntel:
    """Export local intel and upload to the shared server."""

    def __init__(self, export: ExportIntel, transport: IntelTransport, identity: str) -> None:
        """Initialize with export use case, transport, and player identity.

        Args:
            export: Use case for exporting local intel to CSV.
            transport: Transport port for uploading to the server.
            identity: SHA-256 hex hash identifying this player.
        """
        self._export = export
        self._transport = transport
        self._identity = identity

    def execute(self) -> int:
        """Export local intel and upload to the server.

        Returns:
            Total number of records exported.

        Raises:
            IntelDataError: If export/serialization fails.
            IntelTransferError: If upload fails.
        """
        content = self._export.execute()
        self._transport.upload(content, self._identity)
        return content.count("\n")
