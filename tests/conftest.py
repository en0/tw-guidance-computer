"""Shared test fixtures."""

import pytest

from tw_guidance_computer.domain.models import (
    CargoHold,
    CommodityType,
    PlayerStatus,
    Port,
    PortCommodity,
    Sector,
    TradeDirection,
    WarpConnection,
)


@pytest.fixture()
def make_sector():
    def _factory(**kwargs):
        kwargs.setdefault("id", 100)
        kwargs.setdefault("region", "Test Region")
        kwargs.setdefault("explored", True)
        return Sector(**kwargs)

    return _factory


@pytest.fixture()
def make_port():
    def _factory(**kwargs):
        kwargs.setdefault("sector_id", 100)
        kwargs.setdefault("name", "Test Port")
        kwargs.setdefault("port_class", 4)
        kwargs.setdefault("port_type", "SSB")
        kwargs.setdefault("commodities", [])
        return Port(**kwargs)

    return _factory


@pytest.fixture()
def make_port_commodity():
    def _factory(**kwargs):
        kwargs.setdefault("commodity", CommodityType.FUEL_ORE)
        kwargs.setdefault("direction", TradeDirection.SELLING)
        kwargs.setdefault("quantity", 1000)
        kwargs.setdefault("pct", 100)
        return PortCommodity(**kwargs)

    return _factory


@pytest.fixture()
def make_warp():
    def _factory(**kwargs):
        kwargs.setdefault("from_sector", 100)
        kwargs.setdefault("to_sector", 200)
        kwargs.setdefault("explored", True)
        return WarpConnection(**kwargs)

    return _factory


@pytest.fixture()
def make_cargo_hold():
    def _factory(**kwargs):
        kwargs.setdefault("commodity", CommodityType.ORGANICS)
        kwargs.setdefault("quantity", 20)
        kwargs.setdefault("cost_per_unit", 31.5)
        return CargoHold(**kwargs)

    return _factory


@pytest.fixture()
def make_player_status():
    def _factory(**kwargs):
        kwargs.setdefault("sector_id", 100)
        kwargs.setdefault("turns_remaining", 800)
        kwargs.setdefault("credits", 5000)
        kwargs.setdefault("cargo", [])
        kwargs.setdefault("holds_total", 20)
        kwargs.setdefault("holds_empty", 20)
        return PlayerStatus(**kwargs)

    return _factory
