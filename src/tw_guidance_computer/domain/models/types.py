"""Domain type aliases and enums."""

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
