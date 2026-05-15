"""Port for reading game log input."""

from typing import Protocol


class LogReader(Protocol):
    """Reads new chunks of text from the game session log.

    Implementations should handle incremental reading (tail -f style)
    and ANSI stripping.
    """

    def read_new(self) -> str | None:
        """Read any new text available since the last call.

        Returns:
            New text if available, None if no new data.
        """
        ...

    def has_data(self) -> bool:
        """Check if there is data available to read.

        Returns:
            True if new data is waiting.
        """
        ...
