"""Tests for the FindPath use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.find_path import FindPath
from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.domain.exceptions import PathNotFoundError
from tw_guidance_computer.domain.models import WarpConnection


@pytest.fixture()
def mock_store():
    return MagicMock(spec=GameStateReader)


@pytest.fixture()
def find_path(mock_store):
    return FindPath(mock_store)


class TestFindPath:
    def test_direct_path(self, find_path, mock_store):
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
        ]
        path = find_path.execute(100, 200)
        assert path == [100, 200]

    def test_multi_hop_path(self, find_path, mock_store):
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
            WarpConnection(from_sector=200, to_sector=300),
            WarpConnection(from_sector=300, to_sector=400),
        ]
        path = find_path.execute(100, 400)
        assert path == [100, 200, 300, 400]

    def test_same_sector(self, find_path, mock_store):
        mock_store.get_all_warps.return_value = []
        path = find_path.execute(100, 100)
        assert path == [100]

    def test_no_path_raises(self, find_path, mock_store):
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
            WarpConnection(from_sector=300, to_sector=400),
        ]
        with pytest.raises(PathNotFoundError):
            find_path.execute(100, 400)

    def test_uses_bidirectional_warps(self, find_path, mock_store):
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
        ]
        path = find_path.execute(200, 100)
        assert path == [200, 100]
