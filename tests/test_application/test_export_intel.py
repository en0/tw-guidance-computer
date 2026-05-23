"""Tests for the ExportIntel use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.export_intel import ExportIntel
from tw_guidance_computer.application.ports.intel_store import IntelStore
from tw_guidance_computer.domain.models import Planet, Port, Sector, WarpConnection


@pytest.fixture()
def mock_store():
    store = MagicMock(spec=IntelStore)
    store.get_local_sectors.return_value = []
    store.get_local_ports.return_value = []
    store.get_local_warps.return_value = []
    store.get_local_planets.return_value = []
    return store


@pytest.fixture()
def export_intel(mock_store):
    return ExportIntel(mock_store)


class TestExportIntel:
    def test_empty_store_produces_valid_csv(self, export_intel):
        result = export_intel.execute()
        assert "#TYPE:sectors" in result
        assert "#TYPE:ports" in result
        assert "#TYPE:warps" in result
        assert "#TYPE:planets" in result
        assert "#SHA256:" in result

    def test_delegates_to_store(self, export_intel, mock_store):
        export_intel.execute()
        mock_store.get_local_sectors.assert_called_once()
        mock_store.get_local_ports.assert_called_once()
        mock_store.get_local_warps.assert_called_once()
        mock_store.get_local_planets.assert_called_once()

    def test_includes_sector_data(self, export_intel, mock_store):
        mock_store.get_local_sectors.return_value = [
            (Sector(id=616, region="uncharted space", explored=True), 1000.0),
        ]
        result = export_intel.execute()
        assert "616" in result
        assert "uncharted space" in result

    def test_includes_port_data(self, export_intel, mock_store):
        mock_store.get_local_ports.return_value = [
            (Port(sector_id=616, name="Trader Vic's", port_class=6, port_type="SBS"), 1000.0),
        ]
        result = export_intel.execute()
        assert "Trader Vic's" in result
        assert "SBS" in result

    def test_includes_warp_data(self, export_intel, mock_store):
        mock_store.get_local_warps.return_value = [
            (WarpConnection(from_sector=616, to_sector=544, explored=True), 1000.0),
        ]
        result = export_intel.execute()
        assert "616" in result
        assert "544" in result

    def test_includes_planet_data(self, export_intel, mock_store):
        mock_store.get_local_planets.return_value = [
            (Planet(sector_id=616, name="Terra", planet_class="M"), 1000.0),
        ]
        result = export_intel.execute()
        assert "Terra" in result
