"""Domain model: cargo holds and manifest."""

from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class CargoManifest:
    """Immutable cargo manifest with weighted-average cost basis accounting.

    Business rules:
    - No duplicate commodities in holdings
    - Adding an existing commodity merges via weighted average cost
    - Removing more than held removes the commodity entirely
    """

    holdings: list[CargoHold] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate no duplicate commodities."""
        seen: set[CommodityType] = set()
        for hold in self.holdings:
            if hold.commodity in seen:
                raise ValidationError("duplicate commodity in manifest")
            seen.add(hold.commodity)

    def add(self, commodity: CommodityType, quantity: int, cost_per_unit: float) -> CargoManifest:
        """Add cargo using weighted-average cost basis. Returns new manifest.

        Args:
            commodity: The commodity type to add.
            quantity: Number of units to add.
            cost_per_unit: Cost per unit of the new cargo.

        Returns:
            A new CargoManifest with the cargo added.
        """
        result: list[CargoHold] = []
        merged = False
        for hold in self.holdings:
            if hold.commodity == commodity:
                total_qty = hold.quantity + quantity
                avg_cost = (
                    (hold.quantity * hold.cost_per_unit + quantity * cost_per_unit) / total_qty
                    if total_qty > 0
                    else 0.0
                )
                result.append(CargoHold(commodity=commodity, quantity=total_qty, cost_per_unit=avg_cost))
                merged = True
            else:
                result.append(hold)
        if not merged:
            result.append(CargoHold(commodity=commodity, quantity=quantity, cost_per_unit=cost_per_unit))
        return CargoManifest(holdings=result)

    def remove(self, commodity: CommodityType, quantity: int) -> CargoManifest:
        """Remove sold cargo. Returns new manifest.

        Args:
            commodity: The commodity type to remove.
            quantity: Number of units to remove.

        Returns:
            A new CargoManifest with the cargo removed.
        """
        result: list[CargoHold] = []
        for hold in self.holdings:
            if hold.commodity == commodity:
                remaining = hold.quantity - quantity
                if remaining > 0:
                    result.append(CargoHold(commodity=commodity, quantity=remaining, cost_per_unit=hold.cost_per_unit))
            else:
                result.append(hold)
        return CargoManifest(holdings=result)

    @property
    def total_investment(self) -> float:
        """Total credits invested across all cargo."""
        return sum(h.total_cost for h in self.holdings)
