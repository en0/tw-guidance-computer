"""Tests for the FindSafeHarbor use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.find_safe_harbor import FindSafeHarbor
from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.domain.models import Port, Sector, WarpConnection


@pytest.fixture()
def mock_store():
    return MagicMock(spec=GameStateReader)


@pytest.fixture()
def find_safe_harbor(mock_store):
    return FindSafeHarbor(mock_store)


class TestFindSafeHarbor:
    def test_finds_nearest_federation_sector(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = [300]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
            WarpConnection(from_sector=200, to_sector=300),
        ]
        mock_store.get_sector.return_value = Sector(id=300, region="The Federation")
        mock_store.get_port.return_value = None

        result = find_safe_harbor.execute(100)

        assert result is not None
        assert result.destination_sector == 300
        assert result.destination_name == "The Federation"
        assert result.route == [100, 200, 300]
        assert result.hops == 2

    def test_finds_stardock(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = [200]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
        ]
        mock_store.get_sector.return_value = Sector(id=200, region="uncharted space")
        mock_store.get_port.return_value = Port(
            sector_id=200, name="StarDock", port_class=0, port_type="SSS"
        )

        result = find_safe_harbor.execute(100)

        assert result is not None
        assert result.destination_sector == 200
        assert result.destination_name == "StarDock"
        assert result.route == [100, 200]

    def test_returns_none_when_isolated(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = [500]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
            WarpConnection(from_sector=500, to_sector=600),
        ]

        result = find_safe_harbor.execute(100)

        assert result is None

    def test_returns_self_route_when_already_safe(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = [100]
        mock_store.get_sector.return_value = Sector(
            id=100, region="The Federation"
        )
        mock_store.get_port.return_value = Port(
            sector_id=100, name="Sol", port_class=0, port_type="SSS"
        )

        result = find_safe_harbor.execute(100)

        assert result is not None
        assert result.destination_sector == 100
        assert result.destination_name == "The Federation / StarDock"
        assert result.route == [100]
        assert result.hops == 0

    def test_prefers_closer_safe_sector(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = [200, 400]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
            WarpConnection(from_sector=100, to_sector=300),
            WarpConnection(from_sector=300, to_sector=400),
        ]
        mock_store.get_sector.return_value = Sector(id=200, region="The Federation")
        mock_store.get_port.return_value = None

        result = find_safe_harbor.execute(100)

        assert result is not None
        assert result.destination_sector == 200
        assert result.route == [100, 200]
        assert result.hops == 1

    def test_returns_none_when_no_safe_sectors_exist(self, find_safe_harbor, mock_store):
        mock_store.get_safe_sector_ids.return_value = []

        result = find_safe_harbor.execute(100)

        assert result is None
