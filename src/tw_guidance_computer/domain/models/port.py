"""Domain model: ports and port commodities."""

from __future__ import annotations

from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.types import CommodityType, TradeDirection


@dataclass(frozen=True)
class PortCommodity:
    """A single commodity listing at a port."""

    commodity: CommodityType
    direction: TradeDirection
    quantity: int
    pct: int

    def __post_init__(self) -> None:
        """Validate port commodity fields."""
        if self.quantity < 0:
            raise ValidationError("quantity must be non-negative")
        if not (0 <= self.pct <= 100):
            raise ValidationError("pct must be between 0 and 100")


@dataclass(frozen=True)
class Port:
    """A trading port in a sector."""

    sector_id: int
    name: str
    port_class: int
    port_type: str
    commodities: list[PortCommodity] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate port fields."""
        if self.sector_id < 1:
            raise ValidationError("sector_id must be positive")
        if not self.name.strip():
            raise ValidationError("name must not be empty")

    @property
    def type_code(self) -> str:
        """Three-character buy/sell code (e.g., 'SSB', 'BBS')."""
        return self.port_type


@dataclass(frozen=True)
class NearbyPort:
    """A port found within a certain hop distance."""

    hops: int
    port: Port

    def __post_init__(self) -> None:
        """Validate nearby port fields."""
        if self.hops < 0:
            raise ValidationError("hops must be non-negative")
