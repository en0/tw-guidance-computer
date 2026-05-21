"""Use case: find shortest path between two sectors."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.exceptions import PathNotFoundError
from tw_guidance_computer.domain.warp_graph import WarpGraph


@final
class FindPath:
    """BFS shortest path between two sectors using known warps."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, start: int, end: int) -> list[int]:
        """Find the shortest known path between two sectors.

        Args:
            start: Starting sector ID.
            end: Destination sector ID.

        Returns:
            Ordered list of sector IDs from start to end inclusive.

        Raises:
            PathNotFoundError: If no path exists in the known warp graph.
        """
        graph = WarpGraph(self._store.get_all_warps())
        path = graph.bfs_path(start, end)
        if path is None:
            raise PathNotFoundError(f"No known path from {start} to {end}")
        return path
