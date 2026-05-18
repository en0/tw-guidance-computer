"""Domain model: cargo holds."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.types import CommodityType


@dataclass(frozen=True)
class CargoHold:
    """Cargo in the player's hold with cost basis."""

    commodity: CommodityType
    quantity: int
    cost_per_unit: float

    def __post_init__(self) -> None:
        """Validate cargo hold fields."""
        if self.quantity < 0:
            raise ValidationError("quantity must be non-negative")
        if self.cost_per_unit < 0:
            raise ValidationError("cost_per_unit must be non-negative")

    @property
    def total_cost(self) -> float:
        """Total credits invested in this cargo."""
        return self.quantity * self.cost_per_unit
