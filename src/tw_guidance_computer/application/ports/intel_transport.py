"""Port for intel file transport operations."""

from typing import Protocol

from tw_guidance_computer.domain.models import RemoteFile


class IntelTransport(Protocol):
    """Abstracts SFTP file operations for intel sync.

    Stateless — each method invocation is an independent operation.
    No connect/disconnect lifecycle management required.

    All methods raise IntelTransferError on failure.
    """

    def upload(self, content: str, remote_name: str) -> None:
        """Upload content to a remote file.

        The adapter handles temporary file creation internally.

        Args:
            content: The file content to upload.
            remote_name: The destination filename on the server.

        Raises:
            IntelTransferError: If the upload fails.
        """
        ...

    def download(self, remote_name: str) -> str:
        """Download a remote file and return its content.

        Args:
            remote_name: The filename to download from the server.

        Returns:
            The file content as a string.

        Raises:
            IntelTransferError: If the download fails.
        """
        ...

    def list_files(self) -> list[RemoteFile]:
        """List files on the remote server.

        Returns:
            List of RemoteFile entries available on the server.

        Raises:
            IntelTransferError: If the listing fails.
        """
        ...
