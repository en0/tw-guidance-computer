"""SFTP transport adapter — subprocess-based file transfer."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.intel_transport import IntelTransport
from tw_guidance_computer.domain.exceptions import IntelConnectError, IntelTransferError
from tw_guidance_computer.domain.models import IntelConfig, RemoteFile

_CONNECT_ERRORS = re.compile(r"(?i)connection refused|timed out|no route to host")
_AUTH_ERRORS = re.compile(r"(?i)permission denied|authentication failed|no such identity")


def _classify_error(stderr: str, fallback_msg: str) -> IntelConnectError | IntelTransferError:
    """Classify subprocess failure into the appropriate domain exception."""
    if _CONNECT_ERRORS.search(stderr) or _AUTH_ERRORS.search(stderr):
        return IntelConnectError(stderr.strip() or fallback_msg)
    return IntelTransferError(stderr.strip() or fallback_msg)


@final
class SftpTransport(IntelTransport):
    """SFTP file transport using the system sftp binary."""

    def __init__(self, config: IntelConfig) -> None:
        """Initialize with connection configuration.

        Args:
            config: Intel server connection details.
        """
        self._config = config

    def _base_args(self) -> list[str]:
        """Build common sftp command arguments."""
        return [
            "sftp",
            "-i", self._config.key_path,
            "-P", str(self._config.port),
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
        ]

    def _target(self) -> str:
        """Build the user@host target string."""
        return f"intel@{self._config.host}"

    def _run_batch(self, batch_content: str) -> subprocess.CompletedProcess[str]:
        """Execute an sftp batch command.

        Args:
            batch_content: SFTP commands to execute.

        Returns:
            Completed process result.

        Raises:
            IntelConnectError: On connection or auth failure.
            IntelTransferError: On transfer failure.
        """
        batch_file = None
        try:
            batch_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".sftp", delete=False
            )
            batch_file.write(batch_content)
            batch_file.close()

            args = self._base_args() + ["-b", batch_file.name, self._target()]
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise _classify_error(result.stderr, f"sftp failed (exit {result.returncode})")
            return result
        except subprocess.TimeoutExpired as e:
            raise IntelConnectError("SFTP operation timed out") from e
        except OSError as e:
            raise IntelTransferError(f"Failed to execute sftp: {e}") from e
        finally:
            if batch_file is not None:
                Path(batch_file.name).unlink(missing_ok=True)

    @override
    def upload(self, content: str, remote_name: str) -> None:
        """Upload content to a remote file.

        Args:
            content: The file content to upload.
            remote_name: The destination filename on the server.

        Raises:
            IntelConnectError: On connection or auth failure.
            IntelTransferError: If the upload fails.
        """
        local_file = None
        try:
            local_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".csv", delete=False
            )
            local_file.write(content)
            local_file.close()
            self._run_batch(f"put {local_file.name} {remote_name}\n")
        finally:
            if local_file is not None:
                Path(local_file.name).unlink(missing_ok=True)

    @override
    def download(self, remote_name: str) -> str:
        """Download a remote file and return its content.

        Args:
            remote_name: The filename to download from the server.

        Returns:
            The file content as a string.

        Raises:
            IntelConnectError: On connection or auth failure.
            IntelTransferError: If the download fails.
        """
        local_file = None
        try:
            local_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
            local_file.close()
            self._run_batch(f"get {remote_name} {local_file.name}\n")
            return Path(local_file.name).read_text()
        finally:
            if local_file is not None:
                Path(local_file.name).unlink(missing_ok=True)

    @override
    def list_files(self) -> list[RemoteFile]:
        """List files on the remote server.

        Returns:
            List of RemoteFile entries available on the server.

        Raises:
            IntelConnectError: On connection or auth failure.
            IntelTransferError: If the listing fails.
        """
        result = self._run_batch("ls -l\n")
        return _parse_ls_output(result.stdout)


def _parse_ls_output(output: str) -> list[RemoteFile]:
    """Parse sftp ls -l output into RemoteFile objects.

    Expected format per line: -rw-r--r--    1 user  group  1234 May 22 10:00 filename.csv
    """
    files: list[RemoteFile] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("sftp>"):
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        # Skip directories
        if line.startswith("d"):
            continue
        if not parts[4].isdigit():
            continue
        size = int(parts[4])
        name = parts[8]
        files.append(RemoteFile(name=name, size=size))
    return files
