"""Tests for the FindTradePairs use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.domain.models import Port, WarpConnection


@pytest.fixture()
def mock_store():
    return MagicMock(spec=GameStateReader)


@pytest.fixture()
def find_pairs(mock_store):
    return FindTradePairs(mock_store)


class TestFindTradePairs:
    def test_finds_perfect_pair(self, find_pairs, mock_store):
        mock_store.get_all_ports.return_value = [
            Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"),
            Port(sector_id=200, name="Beta", port_class=1, port_type="BBS"),
        ]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
        ]

        pairs = find_pairs.execute()
        assert len(pairs) == 1
        assert pairs[0].complementary_count == 3

    def test_no_pairs_when_not_adjacent(self, find_pairs, mock_store):
        mock_store.get_all_ports.return_value = [
            Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"),
            Port(sector_id=200, name="Beta", port_class=1, port_type="BBS"),
        ]
        mock_store.get_all_warps.return_value = []

        pairs = find_pairs.execute()
        assert len(pairs) == 0

    def test_filters_by_min_complementary(self, find_pairs, mock_store):
        mock_store.get_all_ports.return_value = [
            Port(sector_id=100, name="Alpha", port_class=4, port_type="SSB"),
            Port(sector_id=200, name="Beta", port_class=2, port_type="BSB"),
        ]
        mock_store.get_all_warps.return_value = [
            WarpConnection(from_sector=100, to_sector=200),
        ]

        # SSB vs BSB: Fuel S/B=complement, Org S/S=no, Equip B/B=no → 1 complement
        pairs = find_pairs.execute(min_complementary=2)
        assert len(pairs) == 0

        pairs = find_pairs.execute(min_complementary=1)
        assert len(pairs) == 1
