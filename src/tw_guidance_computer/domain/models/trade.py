"""Domain model: trade pairs and sell recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.types import CommodityType


@dataclass(frozen=True)
class TradeRoute:
    """A single complementary trade between two ports."""

    commodity: CommodityType
    buy_sector: int
    sell_sector: int

    def __post_init__(self) -> None:
        """Validate trade route fields."""
        if self.buy_sector < 1:
            raise ValidationError("buy_sector must be positive")
        if self.sell_sector < 1:
            raise ValidationError("sell_sector must be positive")


@dataclass(frozen=True)
class TradePair:
    """Two adjacent ports with complementary buy/sell patterns."""

    sector_a: int
    sector_b: int
    port_a_name: str
    port_b_name: str
    port_a_type: str
    port_b_type: str
    complementary_count: int
    routes: list[TradeRoute] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate trade pair fields."""
        if self.sector_a < 1:
            raise ValidationError("sector_a must be positive")
        if self.sector_b < 1:
            raise ValidationError("sector_b must be positive")
        if not self.port_a_name.strip():
            raise ValidationError("port_a_name must not be empty")
        if not self.port_b_name.strip():
            raise ValidationError("port_b_name must not be empty")
        if self.complementary_count < 1:
            raise ValidationError("complementary_count must be positive")


@dataclass(frozen=True)
class NearestPair:
    """A trade pair with its distance from a reference sector."""

    hops: int
    pair: TradePair

    def __post_init__(self) -> None:
        """Validate nearest pair fields."""
        if self.hops < 0:
            raise ValidationError("hops must be non-negative")


@dataclass(frozen=True)
class SellRecommendation:
    """A recommendation for where to sell cargo."""

    sector_id: int
    port_name: str
    hops: int
    commodities_accepted: list[CommodityType] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate sell recommendation fields."""
        if self.sector_id < 1:
            raise ValidationError("sector_id must be positive")
        if not self.port_name.strip():
            raise ValidationError("port_name must not be empty")
        if self.hops < 0:
            raise ValidationError("hops must be non-negative")
