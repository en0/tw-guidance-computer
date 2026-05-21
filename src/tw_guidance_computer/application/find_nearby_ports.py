"""Use case: find ports within N hops of a sector."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import NearbyPort
from tw_guidance_computer.domain.warp_graph import WarpGraph


@final
class FindNearbyPorts:
    """BFS to find all ports within a given hop distance."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, sector_id: int, max_hops: int = 5) -> list[NearbyPort]:
        """Find ports reachable within max_hops.

        Args:
            sector_id: Starting sector.
            max_hops: Maximum search distance.

        Returns:
            List of NearbyPort sorted by distance.
        """
        graph = WarpGraph(self._store.get_all_warps())
        distances = graph.bfs_distances(sector_id, max_hops=max_hops)

        results: list[NearbyPort] = []
        for sid, hops in distances.items():
            port = self._store.get_port(sid)
            if port:
                results.append(NearbyPort(hops=hops, port=port))

        results.sort(key=lambda x: x.hops)
        return results
