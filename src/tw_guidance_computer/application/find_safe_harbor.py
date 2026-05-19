"""Use case: find nearest safe harbor via BFS."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import SafeHarborRoute


@final
class FindSafeHarbor:
    """Find the nearest safe sector via BFS."""

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store

    def execute(self, from_sector: int) -> SafeHarborRoute | None:
        """Find the nearest safe sector from the given position.

        Args:
            from_sector: The player's current sector.

        Returns:
            Route to nearest safe sector, or None if no path exists.
        """
        safe_ids = set(self._store.get_safe_sector_ids())
        if not safe_ids:
            return None

        if from_sector in safe_ids:
            return SafeHarborRoute(
                destination_sector=from_sector,
                destination_name=self._build_name(from_sector),
                route=[from_sector],
            )

        warps = self._store.get_all_warps()
        adj: dict[int, set[int]] = defaultdict(set)
        for w in warps:
            adj[w.from_sector].add(w.to_sector)
            adj[w.to_sector].add(w.from_sector)

        queue: deque[tuple[int, list[int]]] = deque([(from_sector, [from_sector])])
        visited = {from_sector}

        while queue:
            current, path = queue.popleft()
            for neighbor in adj[current]:
                if neighbor in safe_ids:
                    route = path + [neighbor]
                    return SafeHarborRoute(
                        destination_sector=neighbor,
                        destination_name=self._build_name(neighbor),
                        route=route,
                    )
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def _build_name(self, sector_id: int) -> str:
        """Build a human-readable name for a safe sector.

        Args:
            sector_id: The sector to name.

        Returns:
            Descriptive name combining Federation and/or StarDock status.
        """
        parts: list[str] = []
        sector = self._store.get_sector(sector_id)
        if sector and sector.region == "The Federation":
            parts.append("The Federation")
        port = self._store.get_port(sector_id)
        if port and port.port_class == 0:
            parts.append("StarDock")
        return " / ".join(parts) if parts else "Safe Sector"
