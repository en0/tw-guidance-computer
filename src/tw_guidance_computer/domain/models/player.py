"""Domain model: player status."""

from __future__ import annotations

from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.cargo import CargoHold


@dataclass(frozen=True)
class PlayerStatus:
    """Current player state snapshot."""

    sector_id: int
    turns_remaining: int
    credits: int
    cargo: list[CargoHold] = field(default_factory=list)
    holds_total: int = 0
    holds_empty: int = 0

    def __post_init__(self) -> None:
        """Validate player status fields."""
        if self.sector_id < 1:
            raise ValidationError("sector_id must be positive")
        if self.turns_remaining < 0:
            raise ValidationError("turns_remaining must be non-negative")
        if self.holds_total < 0:
            raise ValidationError("holds_total must be non-negative")
        if self.holds_empty < 0:
            raise ValidationError("holds_empty must be non-negative")

    @property
    def total_investment(self) -> float:
        """Total credits tied up in cargo."""
        return sum(h.total_cost for h in self.cargo)
