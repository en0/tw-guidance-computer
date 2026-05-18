"""Domain model: database summary and sector detail."""

from __future__ import annotations

from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.port import Port
from tw_guidance_computer.domain.models.sector import Sector, WarpConnection


@dataclass(frozen=True)
class SectorDetail:
    """Full detail view of a sector."""

    sector: Sector
    warps: list[WarpConnection] = field(default_factory=list)
    port: Port | None = None
    warp_ports: dict[int, Port] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate sector detail fields.

        All fields are already-validated domain objects; no additional
        scalar constraints to enforce.
        """


@dataclass(frozen=True)
class DatabaseSummary:
    """Aggregate statistics about the game knowledge base."""

    sectors_total: int
    sectors_explored: int
    ports_total: int
    warps_total: int
    port_type_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate database summary fields."""
        if self.sectors_total < 0:
            raise ValidationError("sectors_total must be non-negative")
        if self.sectors_explored < 0:
            raise ValidationError("sectors_explored must be non-negative")
        if self.ports_total < 0:
            raise ValidationError("ports_total must be non-negative")
        if self.warps_total < 0:
            raise ValidationError("warps_total must be non-negative")
