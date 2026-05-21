"""Tests for CargoManifest domain entity."""

import pytest

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models import CargoHold, CargoManifest, CommodityType


@pytest.fixture()
def make_cargo_manifest():
    def _factory(**kwargs):
        kwargs.setdefault("holdings", [])
        return CargoManifest(**kwargs)

    return _factory


class TestCargoManifestConstruction:
    def test_empty_manifest(self, make_cargo_manifest):
        manifest = make_cargo_manifest()
        assert manifest.holdings == []

    def test_with_holdings(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=5.0)]
        manifest = make_cargo_manifest(holdings=holdings)
        assert len(manifest.holdings) == 1

    def test_duplicate_commodity_raises(self, make_cargo_manifest):
        holdings = [
            CargoHold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=5.0),
            CargoHold(commodity=CommodityType.FUEL_ORE, quantity=5, cost_per_unit=3.0),
        ]
        with pytest.raises(ValidationError, match="duplicate commodity"):
            make_cargo_manifest(holdings=holdings)

    def test_frozen(self, make_cargo_manifest):
        manifest = make_cargo_manifest()
        with pytest.raises(AttributeError):
            manifest.holdings = []  # type: ignore[misc]


class TestCargoManifestAdd:
    def test_add_new_commodity(self, make_cargo_manifest):
        manifest = make_cargo_manifest()
        result = manifest.add(CommodityType.ORGANICS, 20, 31.5)
        assert len(result.holdings) == 1
        assert result.holdings[0].commodity == CommodityType.ORGANICS
        assert result.holdings[0].quantity == 20
        assert result.holdings[0].cost_per_unit == 31.5

    def test_add_merges_weighted_average(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=10.0)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.add(CommodityType.FUEL_ORE, 10, 20.0)
        assert result.holdings[0].quantity == 20
        assert result.holdings[0].cost_per_unit == 15.0

    def test_add_preserves_other_holdings(self, make_cargo_manifest):
        holdings = [
            CargoHold(commodity=CommodityType.FUEL_ORE, quantity=5, cost_per_unit=10.0),
            CargoHold(commodity=CommodityType.ORGANICS, quantity=3, cost_per_unit=20.0),
        ]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.add(CommodityType.EQUIPMENT, 8, 50.0)
        assert len(result.holdings) == 3
        assert result.holdings[0].commodity == CommodityType.FUEL_ORE
        assert result.holdings[1].commodity == CommodityType.ORGANICS

    def test_add_returns_new_instance(self, make_cargo_manifest):
        manifest = make_cargo_manifest()
        result = manifest.add(CommodityType.FUEL_ORE, 10, 5.0)
        assert result is not manifest
        assert manifest.holdings == []

    def test_add_weighted_average_unequal_quantities(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.EQUIPMENT, quantity=30, cost_per_unit=100.0)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.add(CommodityType.EQUIPMENT, 10, 200.0)
        assert result.holdings[0].quantity == 40
        expected_cost = (30 * 100.0 + 10 * 200.0) / 40
        assert result.holdings[0].cost_per_unit == pytest.approx(expected_cost)


class TestCargoManifestRemove:
    def test_remove_partial(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.ORGANICS, quantity=20, cost_per_unit=31.5)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.ORGANICS, 5)
        assert result.holdings[0].quantity == 15
        assert result.holdings[0].cost_per_unit == 31.5

    def test_remove_all(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.ORGANICS, quantity=20, cost_per_unit=31.5)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.ORGANICS, 20)
        assert result.holdings == []

    def test_remove_more_than_held(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.ORGANICS, quantity=10, cost_per_unit=31.5)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.ORGANICS, 15)
        assert result.holdings == []

    def test_remove_preserves_other_holdings(self, make_cargo_manifest):
        holdings = [
            CargoHold(commodity=CommodityType.FUEL_ORE, quantity=5, cost_per_unit=10.0),
            CargoHold(commodity=CommodityType.ORGANICS, quantity=10, cost_per_unit=20.0),
        ]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.ORGANICS, 10)
        assert len(result.holdings) == 1
        assert result.holdings[0].commodity == CommodityType.FUEL_ORE

    def test_remove_nonexistent_commodity(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.FUEL_ORE, quantity=5, cost_per_unit=10.0)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.ORGANICS, 5)
        assert len(result.holdings) == 1
        assert result.holdings[0].commodity == CommodityType.FUEL_ORE

    def test_remove_returns_new_instance(self, make_cargo_manifest):
        holdings = [CargoHold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=5.0)]
        manifest = make_cargo_manifest(holdings=holdings)
        result = manifest.remove(CommodityType.FUEL_ORE, 5)
        assert result is not manifest
        assert manifest.holdings[0].quantity == 10


class TestCargoManifestTotalInvestment:
    def test_empty(self, make_cargo_manifest):
        manifest = make_cargo_manifest()
        assert manifest.total_investment == 0.0

    def test_with_cargo(self, make_cargo_manifest):
        holdings = [
            CargoHold(commodity=CommodityType.FUEL_ORE, quantity=10, cost_per_unit=5.0),
            CargoHold(commodity=CommodityType.ORGANICS, quantity=20, cost_per_unit=30.0),
        ]
        manifest = make_cargo_manifest(holdings=holdings)
        assert manifest.total_investment == 650.0
