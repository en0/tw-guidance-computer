"""Tests for the ImportIntel use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.import_intel import ImportIntel
from tw_guidance_computer.application.ports.intel_store import IntelStore
from tw_guidance_computer.domain.exceptions import IntelDataError
from tw_guidance_computer.domain.intel_csv import serialize_intel
from tw_guidance_computer.domain.models import Planet, Port, Sector, WarpConnection


@pytest.fixture()
def mock_store():
    store = MagicMock(spec=IntelStore)
    store.import_sectors.return_value = 0
    store.import_ports.return_value = 0
    store.import_warps.return_value = 0
    store.import_planets.return_value = 0
    return store


@pytest.fixture()
def import_intel(mock_store):
    return ImportIntel(mock_store)


def _make_csv(sectors=None, ports=None, warps=None, planets=None):
    return serialize_intel(
        sectors or [],
        ports or [],
        warps or [],
        planets or [],
    )


class TestImportIntel:
    def test_empty_csv_returns_zero_result(self, import_intel):
        csv_content = _make_csv()
        result = import_intel.execute(csv_content, "abc123")
        assert result.total == 0

    def test_delegates_sectors_to_store(self, import_intel, mock_store):
        sectors = [(Sector(id=616, region="uncharted space", explored=True), 1000.0)]
        csv_content = _make_csv(sectors=sectors)
        import_intel.execute(csv_content, "abc123")
        mock_store.import_sectors.assert_called_once()
        args = mock_store.import_sectors.call_args
        assert len(args[0][0]) == 1
        assert args[0][1] == "abc123"

    def test_delegates_ports_to_store(self, import_intel, mock_store):
        ports = [(Port(sector_id=616, name="Vic's", port_class=6, port_type="SBS"), 1000.0)]
        csv_content = _make_csv(ports=ports)
        import_intel.execute(csv_content, "src1")
        mock_store.import_ports.assert_called_once()
        args = mock_store.import_ports.call_args
        assert len(args[0][0]) == 1
        assert args[0][1] == "src1"

    def test_delegates_warps_to_store(self, import_intel, mock_store):
        warps = [(WarpConnection(from_sector=616, to_sector=544, explored=True), 1000.0)]
        csv_content = _make_csv(warps=warps)
        import_intel.execute(csv_content, "src1")
        mock_store.import_warps.assert_called_once()

    def test_delegates_planets_to_store(self, import_intel, mock_store):
        planets = [(Planet(sector_id=616, name="Terra", planet_class="M"), 1000.0)]
        csv_content = _make_csv(planets=planets)
        import_intel.execute(csv_content, "src1")
        mock_store.import_planets.assert_called_once()

    def test_aggregates_merge_result(self, import_intel, mock_store):
        mock_store.import_sectors.return_value = 2
        mock_store.import_ports.return_value = 3
        mock_store.import_warps.return_value = 5
        mock_store.import_planets.return_value = 1
        csv_content = _make_csv()
        result = import_intel.execute(csv_content, "src1")
        assert result.sectors_added == 2
        assert result.ports_added == 3
        assert result.warps_added == 5
        assert result.planets_added == 1
        assert result.total == 11

    def test_corrupt_csv_raises_intel_data_error(self, import_intel):
        with pytest.raises(IntelDataError):
            import_intel.execute("garbage data", "src1")

    def test_bad_checksum_raises_intel_data_error(self, import_intel):
        csv_content = _make_csv()
        corrupted = csv_content.replace("#SHA256:", "#SHA256:0000")
        with pytest.raises(IntelDataError):
            import_intel.execute(corrupted, "src1")
