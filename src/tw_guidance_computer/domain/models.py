"""Domain value objects and entities for the TW Guidance Computer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CommodityType(Enum):
    """The three tradeable commodities in TW2002."""

    FUEL_ORE = "Fuel Ore"
    ORGANICS = "Organics"
    EQUIPMENT = "Equipment"


class TradeDirection(Enum):
    """Whether a port is buying or selling a commodity."""

    BUYING = "Buying"
    SELLING = "Selling"


@dataclass(frozen=True)
class Sector:
    """A sector in the TW2002 universe."""

    id: int
    region: str = ""
    explored: bool = False


@dataclass(frozen=True)
class PortCommodity:
    """A single commodity listing at a port."""

    commodity: CommodityType
    direction: TradeDirection
    quantity: int
    pct: int


@dataclass(frozen=True)
class Port:
    """A trading port in a sector."""

    sector_id: int
    name: str
    port_class: int
    port_type: str
    commodities: list[PortCommodity] = field(default_factory=list)

    @property
    def type_code(self) -> str:
        """Three-character buy/sell code (e.g., 'SSB', 'BBS')."""
        return self.port_type


@dataclass(frozen=True)
class WarpConnection:
    """A warp lane between two sectors."""

    from_sector: int
    to_sector: int
    explored: bool = True


@dataclass(frozen=True)
class CargoHold:
    """Cargo in the player's hold with cost basis."""

    commodity: CommodityType
    quantity: int
    cost_per_unit: float

    @property
    def total_cost(self) -> float:
        """Total credits invested in this cargo."""
        return self.quantity * self.cost_per_unit


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
    routes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChatMessage:
    """A chat message from sub-space radio or fed comm-link."""

    sender: str
    message: str
    channel: str
    timestamp: str = ""


@dataclass(frozen=True)
class SellRecommendation:
    """A recommendation for where to sell cargo."""

    sector_id: int
    port_name: str
    hops: int
    commodities_accepted: list[CommodityType] = field(default_factory=list)


@dataclass(frozen=True)
class Planet:
    """A planet in a sector."""

    sector_id: int
    name: str
    planet_class: str

    def __post_init__(self) -> None:
        """Validate planet fields."""
        if self.sector_id < 1:
            raise ValueError("sector_id must be positive")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if len(self.planet_class) != 1 or not self.planet_class.isupper():
            raise ValueError("planet_class must be a single uppercase letter")


@dataclass(frozen=True)
class PlayerStatus:
    """Current player state snapshot."""

    sector_id: int
    turns_remaining: int
    credits: int
    cargo: list[CargoHold] = field(default_factory=list)
    holds_total: int = 0
    holds_empty: int = 0

    @property
    def total_investment(self) -> float:
        """Total credits tied up in cargo."""
        return sum(h.total_cost for h in self.cargo)
