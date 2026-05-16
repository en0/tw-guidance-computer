"""Tests for domain models."""

import pytest

from tw_guidance_computer.domain.models import (
    CommodityType,
)


class TestSector:
    def test_construction(self, make_sector):
        sector = make_sector(id=42, region="The Federation")
        assert sector.id == 42
        assert sector.region == "The Federation"
        assert sector.explored is True

    def test_defaults(self, make_sector):
        sector = make_sector()
        assert sector.id == 100


class TestPort:
    def test_type_code(self, make_port):
        port = make_port(port_type="SSB")
        assert port.type_code == "SSB"

    def test_with_commodities(self, make_port, make_port_commodity):
        commodities = [make_port_commodity(quantity=2000)]
        port = make_port(commodities=commodities)
        assert port.commodities[0].quantity == 2000


class TestPlanet:
    def test_construction(self, make_planet):
        planet = make_planet(sector_id=1, name="Terra", planet_class="M")
        assert planet.sector_id == 1
        assert planet.name == "Terra"
        assert planet.planet_class == "M"

    def test_frozen(self, make_planet):
        planet = make_planet()
        with pytest.raises(AttributeError):
            planet.name = "other"  # type: ignore[misc]

    def test_invalid_sector_id(self, make_planet):
        with pytest.raises(ValueError, match="sector_id must be positive"):
            make_planet(sector_id=0)

    def test_empty_name(self, make_planet):
        with pytest.raises(ValueError, match="name must not be empty"):
            make_planet(name="   ")

    def test_invalid_planet_class_lowercase(self, make_planet):
        with pytest.raises(ValueError, match="planet_class must be a single uppercase letter"):
            make_planet(planet_class="m")

    def test_invalid_planet_class_multi_char(self, make_planet):
        with pytest.raises(ValueError, match="planet_class must be a single uppercase letter"):
            make_planet(planet_class="MM")


class TestCargoHold:
    def test_total_cost(self, make_cargo_hold):
        hold = make_cargo_hold(quantity=20, cost_per_unit=31.5)
        assert hold.total_cost == 630.0

    def test_zero_cost(self, make_cargo_hold):
        hold = make_cargo_hold(cost_per_unit=0.0)
        assert hold.total_cost == 0.0


class TestPlayerStatus:
    def test_total_investment(self, make_player_status, make_cargo_hold):
        cargo = [
            make_cargo_hold(commodity=CommodityType.ORGANICS, quantity=10, cost_per_unit=30.0),
            make_cargo_hold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=15.0),
        ]
        status = make_player_status(cargo=cargo)
        assert status.total_investment == 450.0

    def test_empty_cargo(self, make_player_status):
        status = make_player_status()
        assert status.total_investment == 0.0
