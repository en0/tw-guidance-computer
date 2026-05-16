"""Tests for the ParseLogChunk use case."""

import pytest

from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.domain.models import CommodityType


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

    def test_cargo_not_inferred_from_onboard_column(self, parser, store):
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
        # Cargo is tracked via transactions and sync points, not OnBoard column
        assert status.cargo == []

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


class TestInfoBlockSync:
    def test_parses_info_with_cargo(self, parser, store):
        text = (
            "<Info>\n"
            "\n"
            "Trader Name    : Nuisance 1st Class en[0]\n"
            "Rank and Exp   : 14 points, Alignment=-1 Rude\n"
            "Corp# 6, Yukon Gold Sachs\n"
            "Ship Name      : PlantExpress\n"
            "Ship Info      : Talos Merchant Cruiser Ported=93 Kills=0\n"
            "Date Built     : 12:38:43 AM Fri May 15, 2054\n"
            "Turns to Warp  : 3\n"
            "Current Sector : 178\n"
            "Turns left     : 153\n"
            "Total Holds    : 50 - Organics=2 Empty=48\n"
            "Fighters       : 30\n"
            "Shield points  : 312\n"
            "Credits        : 7\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 178
        assert status.turns_remaining == 153
        assert status.credits == 7
        assert status.holds_total == 50
        assert status.holds_empty == 48
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.ORGANICS
        assert status.cargo[0].quantity == 2

    def test_parses_info_with_full_cargo(self, parser, store):
        text = (
            "<Info>\n"
            "\n"
            "Trader Name    : Nuisance 2nd Class en[0]\n"
            "Rank and Exp   : 5 points, Alignment=-1 Rude\n"
            "Corp# 6, Yukon Gold Sachs\n"
            "Ship Name      : PlantExpress\n"
            "Ship Info      : Talos Merchant Cruiser Ported=23 Kills=0\n"
            "Date Built     : 12:38:43 AM Fri May 15, 2054\n"
            "Turns to Warp  : 3\n"
            "Current Sector : 480\n"
            "Turns left     : 764\n"
            "Total Holds    : 20 - Fuel Ore=20\n"
            "Fighters       : 30\n"
            "Shield points  : 5\n"
            "Credits        : 2,872\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 480
        assert status.turns_remaining == 764
        assert status.credits == 2872
        assert status.holds_total == 20
        assert status.holds_empty == 0
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20

    def test_parses_info_empty_holds(self, parser, store):
        text = (
            "<Info>\n"
            "\n"
            "Trader Name    : Civilian en[0]\n"
            "Rank and Exp   : 1 points, Alignment=0 Neutral\n"
            "Ship Name      : pizzasauce\n"
            "Ship Info      : Animoso Merchant Cruiser Ported=86 Kills=0\n"
            "Date Built     : 05:14:58 AM Fri May 15, 2054\n"
            "Turns to Warp  : 3\n"
            "Current Sector : 1\n"
            "Turns left     : 282\n"
            "Total Holds    : 20 - Empty=20\n"
            "Fighters       : 30\n"
            "Credits        : 50,219\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 1
        assert status.turns_remaining == 282
        assert status.credits == 50219
        assert status.holds_total == 20
        assert status.holds_empty == 20
        assert status.cargo == []


class TestStatusBarSync:
    def test_parses_compact_status_bar(self, parser, store):
        text = (
            " Sect 1\u2502Turns 282\u2502Creds 50,219\u2502Figs 30\u2502Shlds 0"
            "\u2502Hlds 20\u2502Ore 0\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 1
        assert status.turns_remaining == 282
        assert status.credits == 50219
        assert status.holds_total == 20
        assert status.holds_empty == 20
        assert status.cargo == []

    def test_parses_status_bar_with_cargo(self, parser, store):
        text = (
            " Sect 480\u2502Turns 764\u2502Creds 2,872\u2502Figs 30\u2502Shlds 5"
            "\u2502Hlds 20\u2502Ore 20\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 480
        assert status.turns_remaining == 764
        assert status.credits == 2872
        assert status.holds_total == 20
        assert status.holds_empty == 0
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20

    def test_parses_status_bar_with_comma_in_turns(self, parser, store):
        text = (
            " Sect 616\u2502Turns 1,000\u2502Creds 25\u2502Figs 1\u2502Shlds 30"
            "\u2502Hlds 1\u2502Ore 0\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 616
        assert status.turns_remaining == 1000
        assert status.credits == 25
        assert status.holds_total == 1
        assert status.holds_empty == 1


class TestTurnCounterFormats:
    def test_stardate_turns(self, parser, store):
        text = (
            "Sector  : 178 in uncharted space.\n"
            "Warps to Sector(s) :  120 - (509)\n"
            "Command [TL=00:00:00]:[178] (?=Help)? :?\n"
            "You have 816 turns this Stardate.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.turns_remaining == 816

    def test_you_have_n_turns_left(self, parser, store):
        text = (
            "Sector  : 246 in uncharted space.\n"
            "Command [TL=00:00:00]:[246] (?=Help)? :P\n"
            "You have 4 turns left.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.turns_remaining == 4

    def test_no_turns_left(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[827] (?=Help)? :P\n"
            "You don't have any turns left.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.turns_remaining == 0

    def test_recover_turns(self, parser, store):
        text = (
            "Sector  : 558 in Actacon (unexplored).\n"
            "Command [TL=00:00:00]:[558] (?=Help)? :N\n"
            "One turn deducted, 100 turns left.\n"
            "You recover 41 of your turns.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert status.turns_remaining == 141


class TestTransactionTracking:
    def test_buy_transaction_with_cost_basis(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[8] (?=Help)? :P\n"
            "One turn deducted, 965 turns left.\n"
            "Commerce report for Aegeus II: 05:21:12 AM Fri May 15, 2054\n"
            "Fuel Ore   Selling   1300    100%       0\n"
            "Organics   Buying    1950    100%       0\n"
            "Equipment  Buying    1950    100%       0\n"
            "\n"
            "You have 300 credits and 20 empty cargo holds.\n"
            "\n"
            "We are selling up to 1300.  You have 0 in your holds.\n"
            "How many holds of Fuel Ore do you want to buy [20]?\n"
            "Agreed, 20 units.\n"
            "\n"
            "We'll sell them for 113 credits.\n"
            "Your offer [113] ?100\n"
            "\n"
            "We'll sell them for 111 credits.\n"
            "Your offer [111] ?\n"
            "You are a shrewd trader, they're all yours.\n"
            "\n"
            "You have 189 credits and 0 empty cargo holds.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20
        assert status.cargo[0].cost_per_unit == pytest.approx(111.0 / 20)

    def test_sell_transaction_removes_cargo(self, parser, store):
        # Pre-load cargo via info block
        info_text = (
            "<Info>\n"
            "\n"
            "Trader Name    : test\n"
            "Ship Name      : test\n"
            "Ship Info      : test\n"
            "Date Built     : 01:00:00 AM Fri May 15, 2054\n"
            "Turns to Warp  : 3\n"
            "Current Sector : 2\n"
            "Turns left     : 961\n"
            "Total Holds    : 20 - Fuel Ore=20\n"
            "Fighters       : 30\n"
            "Credits        : 189\n"
        )
        parser.execute(info_text)

        sell_text = (
            "Command [TL=00:00:00]:[2] (?=Help)? :P\n"
            "One turn deducted, 961 turns left.\n"
            "Commerce report for New Kennedy: 05:21:42 AM Fri May 15, 2054\n"
            "Fuel Ore   Buying    2340    100%      20\n"
            "Organics   Selling   1260    100%       0\n"
            "Equipment  Buying    2390    100%       0\n"
            "\n"
            "You have 189 credits and 0 empty cargo holds.\n"
            "\n"
            "We are buying up to 2340.  You have 20 in your holds.\n"
            "How many holds of Fuel Ore do you want to sell [20]?\n"
            "Agreed, 20 units.\n"
            "\n"
            "We'll buy them for 801 credits.\n"
            "Your offer [801] ?830\n"
            "You insult my intelligence, but we'll buy them anyway.\n"
            "\n"
            "You have 1,019 credits and 20 empty cargo holds.\n"
        )
        parser.execute(sell_text)
        status = store.get_player_status()
        assert status is not None
        assert status.cargo == []
        assert status.holds_empty == 20

    def test_buy_then_sell_full_cycle(self, parser, store):
        text = (
            "Command [TL=00:00:00]:[8] (?=Help)? :P\n"
            "One turn deducted, 957 turns left.\n"
            "Commerce report for Aegeus II: 05:22:15 AM Fri May 15, 2054\n"
            "Fuel Ore   Selling   1280     98%       0\n"
            "Organics   Buying    1950    100%      20\n"
            "Equipment  Buying    1950    100%       0\n"
            "\n"
            "You have 419 credits and 0 empty cargo holds.\n"
            "\n"
            "We are buying up to 1950.  You have 20 in your holds.\n"
            "How many holds of Organics do you want to sell [20]?\n"
            "Agreed, 20 units.\n"
            "\n"
            "We'll buy them for 1,307 credits.\n"
            "Your offer [1,307] ?1320\n"
            "Oh well, maybe I can sell these to some other fool, we'll take them.\n"
            "\n"
            "You have 1,739 credits and 20 empty cargo holds.\n"
            "\n"
            "We are selling up to 1280.  You have 0 in your holds.\n"
            "How many holds of Fuel Ore do you want to buy [20]?\n"
            "Agreed, 20 units.\n"
            "\n"
            "We'll sell them for 119 credits.\n"
            "Your offer [119] ?100\n"
            "\n"
            "We'll sell them for 116 credits.\n"
            "Your offer [116] ?\n"
            "Cheapskate.  Here, take them and leave me alone.\n"
            "\n"
            "You have 1,623 credits and 0 empty cargo holds.\n"
        )
        parser.execute(text)
        status = store.get_player_status()
        assert status is not None
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20
        assert status.cargo[0].cost_per_unit == pytest.approx(116.0 / 20)
        assert status.credits == 1623
