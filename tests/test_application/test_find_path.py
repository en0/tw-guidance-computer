"""Tests for the FindPath use case."""

import pytest

from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.find_path import FindPath
from tw_guidance_computer.domain.exceptions import PathNotFoundError
from tw_guidance_computer.domain.models import WarpConnection


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


@pytest.fixture()
def find_path(store):
    return FindPath(store)


class TestFindPath:
    def test_direct_path(self, store, find_path):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        path = find_path.execute(100, 200)
        assert path == [100, 200]

    def test_multi_hop_path(self, store, find_path):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.upsert_warp(WarpConnection(from_sector=200, to_sector=300))
        store.upsert_warp(WarpConnection(from_sector=300, to_sector=400))
        path = find_path.execute(100, 400)
        assert path == [100, 200, 300, 400]

    def test_same_sector(self, store, find_path):
        path = find_path.execute(100, 100)
        assert path == [100]

    def test_no_path_raises(self, store, find_path):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.upsert_warp(WarpConnection(from_sector=300, to_sector=400))
        with pytest.raises(PathNotFoundError):
            find_path.execute(100, 400)

    def test_uses_bidirectional_warps(self, store, find_path):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        # Should be able to go 200 -> 100 even though only 100->200 is recorded
        path = find_path.execute(200, 100)
        assert path == [200, 100]
