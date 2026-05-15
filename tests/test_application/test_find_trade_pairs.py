"""Tests for the FindTradePairs use case."""

import pytest

from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.domain.models import Port, Sector, WarpConnection


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


@pytest.fixture()
def find_pairs(store):
    return FindTradePairs(store)


class TestFindTradePairs:
    def test_finds_perfect_pair(self, store, find_pairs):
        store.upsert_sector(Sector(id=100, region="A", explored=True))
        store.upsert_sector(Sector(id=200, region="B", explored=True))
        store.upsert_port(Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"))
        store.upsert_port(Port(sector_id=200, name="Beta", port_class=1, port_type="BBS"))
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))

        pairs = find_pairs.execute()
        assert len(pairs) == 1
        assert pairs[0].complementary_count == 3

    def test_no_pairs_when_not_adjacent(self, store, find_pairs):
        store.upsert_sector(Sector(id=100, region="A", explored=True))
        store.upsert_sector(Sector(id=200, region="B", explored=True))
        store.upsert_port(Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"))
        store.upsert_port(Port(sector_id=200, name="Beta", port_class=1, port_type="BBS"))
        # No warp between them

        pairs = find_pairs.execute()
        assert len(pairs) == 0

    def test_filters_by_min_complementary(self, store, find_pairs):
        store.upsert_sector(Sector(id=100, region="A", explored=True))
        store.upsert_sector(Sector(id=200, region="B", explored=True))
        store.upsert_port(Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"))
        store.upsert_port(Port(sector_id=200, name="Beta", port_class=2, port_type="BSB"))
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))

        # Only 1 complementary (Equipment: S at 100, B at 200) — wait, let me check
        # SSB: S-fuel, S-org, B-equip
        # BSB: B-fuel, S-org, B-equip
        # Fuel: S vs B = complement. Org: S vs S = no. Equip: B vs B = no.
        # Only 1 complement, so min_complementary=2 should filter it out
        pairs = find_pairs.execute(min_complementary=2)
        assert len(pairs) == 0

        pairs = find_pairs.execute(min_complementary=1)
        assert len(pairs) == 1
