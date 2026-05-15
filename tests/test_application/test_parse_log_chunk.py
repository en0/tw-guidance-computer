"""Tests for the ParseLogChunk use case."""

import pytest

from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


@pytest.fixture()
def parser(store):
    return ParseLogChunk(store)


class TestParseLogChunk:
    def test_extracts_sector(self, parser, store):
        text = "Sector  : 865 in The Rovine Nebulae.\n"
        parser.execute(text)
        sector = store.get_sector(865)
        assert sector is not None
        assert sector.region == "The Rovine Nebulae"
        assert sector.explored is True

    def test_extracts_warps(self, parser, store):
        text = "Sector  : 865 in The Rovine Nebulae.\nWarps to Sector(s) :  120 - (131) - 658 - (985)\nCommand"
        parser.execute(text)
        warps = store.get_warps(865)
        assert len(warps) == 4
        to_sectors = {w.to_sector for w in warps}
        assert to_sectors == {120, 131, 658, 985}

    def test_unexplored_warps_marked(self, parser, store):
        text = "Sector  : 865 in The Rovine Nebulae.\nWarps to Sector(s) :  120 - (131) - 658\nCommand"
        parser.execute(text)
        sector_131 = store.get_sector(131)
        assert sector_131 is not None
        assert sector_131.explored is False

    def test_extracts_port_from_sector_display(self, parser, store):
        text = (
            "Sector  : 832 in The Rovine Nebulae.\n"
            "Ports   : Nambu Minor, Class 3 (SBB)\n"
            "Warps to Sector(s) :  658\nCommand"
        )
        parser.execute(text)
        port = store.get_port(832)
        assert port is not None
        assert port.name == "Nambu Minor"
        assert port.port_class == 3
        assert port.port_type == "SBB"

    def test_extracts_commerce_report(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[865] (?=Help)? : P\n"
            "Commerce report for Hydra Annex: 01:39:28 AM Fri May 15, 2054\n"
            "Fuel Ore   Selling   2570    100%       0\n"
            "Organics   Selling    760    100%       0\n"
            "Equipment  Selling   1680    100%       0\n"
        )
        parser.execute(text)
        port = store.get_port(865)
        assert port is not None
        assert port.name == "Hydra Annex"
        assert port.port_type == "SSS"
        assert len(port.commodities) == 3

    def test_extracts_turns_remaining(self, parser, store):
        text = (
            "Sector  : 100 in Test.\n"
            "Warps to Sector(s) :  200\n"
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "One turn deducted, 809 turns left.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.turns_remaining == 809

    def test_extracts_credits(self, parser, store):
        text = (
            "Sector  : 100 in Test.\n"
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "You have 5,125 credits and 20 empty cargo holds.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.credits == 5125
        assert status.holds_empty == 20

    def test_cargo_uses_last_commerce_report_only(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "Commerce report for Port Alpha: 01:00:00 AM Fri May 15, 2054\n"
            "Fuel Ore   Buying    1000    100%      20\n"
            "Organics   Selling   2000    100%       0\n"
            "Equipment  Selling   1500    100%       0\n"
            "You have 5,000 credits and 0 empty cargo holds.\n"
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "Commerce report for Port Beta: 01:05:00 AM Fri May 15, 2054\n"
            "Fuel Ore   Selling   1000    100%      10\n"
            "Organics   Buying    2000    100%       5\n"
            "Equipment  Selling   1500    100%       0\n"
            "You have 6,000 credits and 0 empty cargo holds.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        # 0 empty holds after last report means holds are full — use OnBoard values
        assert len(status.cargo) == 2

    def test_cargo_cleared_when_holds_empty_after_commerce(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[827] (?=Help)? : P\n"
            "Commerce report for Augsburg Major: 02:57:31 AM Fri May 15, 2054\n"
            "Fuel Ore   Buying    1364     83%      50\n"
            "Organics   Buying    2050     77%       0\n"
            "Equipment  Selling   1560     58%       0\n"
            "You have 30,211 credits and 0 empty cargo holds.\n"
            "Command [TL=00:00:00]:[827] (?=Help)? : P\n"
            "You have 32,211 credits and 50 empty cargo holds.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        # The last "empty cargo holds" line shows 50 empty AFTER the commerce
        # report, meaning cargo was sold — should be empty
        assert status.cargo == []
        assert status.holds_empty == 50
        assert status.credits == 32211
