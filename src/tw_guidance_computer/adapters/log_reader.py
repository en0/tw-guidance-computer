"""Log reader adapter — tails a script log file and strips ANSI."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.log_reader import LogReader

ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[A-Za-z]"
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"
    r"|\x1b[()][0-9A-Za-z]"
)
CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences and control characters."""
    text = ANSI_RE.sub("", text)
    text = CTRL_RE.sub("", text)
    return text


@final
class TailLogReader(LogReader):
    """Reads new data from a log file using tail-f semantics."""

    def __init__(self, log_path: Path) -> None:
        """Initialize the tail reader.

        Args:
            log_path: Path to the log file to tail.
        """
        self._path = log_path
        self._fd = open(log_path, "rb")  # noqa: SIM115
        # Seek to end so we only process new data going forward
        self._fd.seek(0, os.SEEK_END)
        self._offset = self._fd.tell()

    @override
    def read_new(self) -> str | None:
        """Read any new bytes appended since last read.

        Returns:
            ANSI-stripped text if new data available, None otherwise.
        """
        self._fd.seek(self._offset)
        data = self._fd.read()
        if not data:
            return None
        self._offset = self._fd.tell()
        text = data.decode("utf-8", errors="replace")
        return strip_ansi(text)

    @override
    def has_data(self) -> bool:
        """Check if the file has grown since last read."""
        try:
            size = os.path.getsize(self._path)
            return size > self._offset
        except OSError:
            return False

    def read_full(self) -> str:
        """Read the entire file from the beginning (for initial parse).

        Returns:
            ANSI-stripped full file contents.
        """
        with open(self._path, "rb") as f:
            data = f.read()
        self._offset = len(data)
        self._fd.seek(self._offset)
        text = data.decode("utf-8", errors="replace")
        return strip_ansi(text)

    def close(self) -> None:
        """Close the file descriptor."""
        self._fd.close()
