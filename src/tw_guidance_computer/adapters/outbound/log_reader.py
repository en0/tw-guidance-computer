"""Log reader adapter — tails a script log file and strips ANSI."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.log_reader import LogReader
from tw_guidance_computer.domain.exceptions import LogReadError

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

        Raises:
            LogReadError: If the log file cannot be opened.
        """
        self._path = log_path
        self._partial: str = ""
        try:
            self._fd = open(log_path, "rb")  # noqa: SIM115
            self._fd.seek(0, os.SEEK_END)
            self._offset = self._fd.tell()
        except OSError as e:
            raise LogReadError(f"Cannot open log file {log_path}: {e}") from e

    @override
    def read_new(self) -> str | None:
        """Read any new bytes appended since last read.

        Returns:
            ANSI-stripped text if new data available, None otherwise.
            Holds back the last incomplete line until a newline arrives.

        Raises:
            LogReadError: If reading fails.
        """
        try:
            self._fd.seek(self._offset)
            data = self._fd.read()
        except OSError as e:
            raise LogReadError(f"Failed to read log: {e}") from e
        if not data:
            return None
        self._offset = self._fd.tell()
        text = self._partial + data.decode("utf-8", errors="replace")
        # Hold back the last incomplete line
        last_nl = text.rfind("\n")
        if last_nl == -1:
            # No complete line yet — buffer everything
            self._partial = text
            return None
        self._partial = text[last_nl + 1:]
        return strip_ansi(text[:last_nl + 1])

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

        Raises:
            LogReadError: If reading fails.
        """
        try:
            with open(self._path, "rb") as f:
                data = f.read()
        except OSError as e:
            raise LogReadError(f"Failed to read log file: {e}") from e
        self._offset = len(data)
        self._fd.seek(self._offset)
        text = data.decode("utf-8", errors="replace")
        return strip_ansi(text)

    def close(self) -> None:
        """Close the file descriptor."""
        self._fd.close()
