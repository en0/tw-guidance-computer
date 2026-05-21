"""Domain model: ports and port commodities."""

from __future__ import annotations

from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.types import CommodityType, TradeDirection

_COMMODITY_ORDER = [CommodityType.FUEL_ORE, CommodityType.ORGANICS, CommodityType.EQUIPMENT]


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

    @property
    def buying_commodities(self) -> set[CommodityType]:
        """Return the set of commodity types this port buys.

        Derives from port_type code (B=buying at position i) and
        falls back to commodity detail records if available.
        """
        buying: set[CommodityType] = set()
        if len(self.port_type) == 3:
            for i, c in enumerate(_COMMODITY_ORDER):
                if self.port_type[i] == "B":
                    buying.add(c)
        for pc in self.commodities:
            if pc.direction == TradeDirection.BUYING:
                buying.add(pc.commodity)
        return buying

    def complementary_trades(self, other: Port) -> list[tuple[CommodityType, int, int]]:
        """Find complementary trades between this port and another.

        Returns a list of (commodity, buy_sector, sell_sector) tuples for
        each commodity where one port sells and the other buys.

        Args:
            other: The other port to compare against.

        Returns:
            List of complementary trade tuples.
        """
        if len(self.port_type) != 3 or len(other.port_type) != 3:
            return []
        result: list[tuple[CommodityType, int, int]] = []
        for i, c in enumerate(_COMMODITY_ORDER):
            self_dir = self.port_type[i]
            other_dir = other.port_type[i]
            if self_dir == "S" and other_dir == "B":
                result.append((c, self.sector_id, other.sector_id))
            elif self_dir == "B" and other_dir == "S":
                result.append((c, other.sector_id, self.sector_id))
        return result


@dataclass(frozen=True)
class NearbyPort:
    """A port found within a certain hop distance."""

    hops: int
    port: Port

    def __post_init__(self) -> None:
        """Validate nearby port fields."""
        if self.hops < 0:
            raise ValidationError("hops must be non-negative")
