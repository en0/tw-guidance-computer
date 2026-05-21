"""Tests for Port domain model trade logic."""

import pytest

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models import CommodityType, PortCommodity, TradeDirection, TradeRoute


class TestBuyingCommodities:
    def test_bbs_buys_fuel_and_organics(self, make_port):
        port = make_port(port_type="BBS")
        assert port.buying_commodities == {CommodityType.FUEL_ORE, CommodityType.ORGANICS}

    def test_ssb_buys_equipment(self, make_port):
        port = make_port(port_type="SSB")
        assert port.buying_commodities == {CommodityType.EQUIPMENT}

    def test_sss_buys_nothing(self, make_port):
        port = make_port(port_type="SSS")
        assert port.buying_commodities == set()

    def test_bbb_buys_all(self, make_port):
        port = make_port(port_type="BBB")
        assert port.buying_commodities == {
            CommodityType.FUEL_ORE,
            CommodityType.ORGANICS,
            CommodityType.EQUIPMENT,
        }

    def test_includes_commodity_detail_records(self, make_port):
        commodities = [
            PortCommodity(
                commodity=CommodityType.ORGANICS,
                direction=TradeDirection.BUYING,
                quantity=500,
                pct=50,
            ),
        ]
        port = make_port(port_type="SSS", commodities=commodities)
        assert CommodityType.ORGANICS in port.buying_commodities

    def test_special_port_type_uses_commodity_records(self, make_port):
        commodities = [
            PortCommodity(
                commodity=CommodityType.FUEL_ORE,
                direction=TradeDirection.BUYING,
                quantity=1000,
                pct=100,
            ),
        ]
        port = make_port(port_type="Special", commodities=commodities)
        assert port.buying_commodities == {CommodityType.FUEL_ORE}


class TestComplementaryTrades:
    def test_perfect_complement_ssb_bbs(self, make_port):
        port_a = make_port(sector_id=100, port_type="SSB")
        port_b = make_port(sector_id=200, port_type="BBS")
        trades = port_a.complementary_trades(port_b)
        assert len(trades) == 3
        assert (CommodityType.FUEL_ORE, 100, 200) in trades
        assert (CommodityType.ORGANICS, 100, 200) in trades
        assert (CommodityType.EQUIPMENT, 200, 100) in trades

    def test_no_complement_same_type(self, make_port):
        port_a = make_port(sector_id=100, port_type="SSB")
        port_b = make_port(sector_id=200, port_type="SSB")
        trades = port_a.complementary_trades(port_b)
        assert trades == []

    def test_partial_complement(self, make_port):
        port_a = make_port(sector_id=100, port_type="SSB")
        port_b = make_port(sector_id=200, port_type="BSS")
        trades = port_a.complementary_trades(port_b)
        # Fuel: S/B=complement, Org: S/S=no, Equ: B/S=complement
        assert len(trades) == 2
        assert (CommodityType.FUEL_ORE, 100, 200) in trades
        assert (CommodityType.EQUIPMENT, 200, 100) in trades

    def test_special_port_type_returns_empty(self, make_port):
        port_a = make_port(sector_id=100, port_type="SSB")
        port_b = make_port(sector_id=200, port_type="Special")
        assert port_a.complementary_trades(port_b) == []

    def test_short_port_type_returns_empty(self, make_port):
        port_a = make_port(sector_id=100, port_type="SS")
        port_b = make_port(sector_id=200, port_type="BBS")
        assert port_a.complementary_trades(port_b) == []


class TestTradeRoute:
    def test_construction(self):
        route = TradeRoute(
            commodity=CommodityType.FUEL_ORE,
            buy_sector=100,
            sell_sector=200,
        )
        assert route.commodity == CommodityType.FUEL_ORE
        assert route.buy_sector == 100
        assert route.sell_sector == 200

    def test_invalid_buy_sector(self):
        with pytest.raises(ValidationError, match="buy_sector must be positive"):
            TradeRoute(commodity=CommodityType.FUEL_ORE, buy_sector=0, sell_sector=200)

    def test_invalid_sell_sector(self):
        with pytest.raises(ValidationError, match="sell_sector must be positive"):
            TradeRoute(commodity=CommodityType.FUEL_ORE, buy_sector=100, sell_sector=0)
