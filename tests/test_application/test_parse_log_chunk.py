"""Tests for the ParseLogChunk use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.ports.game_state_writer import GameStateWriter
from tw_guidance_computer.domain.models import (
    CommodityType,
    PlayerStatus,
    Port,
    Sector,
)


@pytest.fixture()
def mock_store():
    store = MagicMock(spec=GameStateWriter)
    return store


@pytest.fixture()
def parser(mock_store):
    return ParseLogChunk(mock_store)


def _last_player_status(mock_store) -> PlayerStatus:
    """Get the last PlayerStatus passed to set_player_status."""
    mock_store.set_player_status.assert_called()
    return mock_store.set_player_status.call_args[0][0]


class TestParseLogChunk:
    def test_extracts_sector(self, parser, mock_store):
        text = "Sector  : 865 in The Rovine Nebulae.\n"
        parser.execute(text)
        mock_store.upsert_sector.assert_any_call(
            Sector(id=865, region="The Rovine Nebulae", explored=True)
        )

    def test_extracts_warps(self, parser, mock_store):
        text = "Sector  : 865 in The Rovine Nebulae.\nWarps to Sector(s) :  120 - (131) - 658 - (985)\nCommand"
        parser.execute(text)
        warp_calls = [c[0][0] for c in mock_store.upsert_warp.call_args_list]
        to_sectors = {w.to_sector for w in warp_calls if w.from_sector == 865}
        assert to_sectors == {120, 131, 658, 985}

    def test_unexplored_warps_marked(self, parser, mock_store):
        text = "Sector  : 865 in The Rovine Nebulae.\nWarps to Sector(s) :  120 - (131) - 658\nCommand"
        parser.execute(text)
        mock_store.upsert_sector.assert_any_call(
            Sector(id=131, explored=False)
        )

    def test_extracts_port_from_sector_display(self, parser, mock_store):
        text = (
            "Sector  : 832 in The Rovine Nebulae.\n"
            "Ports   : Nambu Minor, Class 3 (SBB)\n"
            "Warps to Sector(s) :  658\nCommand"
        )
        parser.execute(text)
        mock_store.upsert_port.assert_any_call(
            Port(sector_id=832, name="Nambu Minor", port_class=3, port_type="SBB")
        )

    def test_extracts_commerce_report(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[865] (?=Help)? : P\n"
            "Commerce report for Hydra Annex: 01:39:28 AM Fri May 15, 2054\n"
            "Fuel Ore   Selling   2570    100%       0\n"
            "Organics   Selling    760    100%       0\n"
            "Equipment  Selling   1680    100%       0\n"
        )
        parser.execute(text)
        port_calls = [c[0][0] for c in mock_store.upsert_port.call_args_list]
        commerce_port = next(p for p in port_calls if p.name == "Hydra Annex")
        assert commerce_port.port_type == "SSS"
        assert len(commerce_port.commodities) == 3

    def test_extracts_turns_remaining(self, parser, mock_store):
        text = (
            "Sector  : 100 in Test.\n"
            "Warps to Sector(s) :  200\n"
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "One turn deducted, 809 turns left.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 809

    def test_extracts_credits(self, parser, mock_store):
        text = (
            "Sector  : 100 in Test.\n"
            "Command [TL=00:00:00]:[100] (?=Help)? : P\n"
            "You have 5,125 credits and 20 empty cargo holds.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.credits == 5125
        assert status.holds_empty == 20

    def test_cargo_not_inferred_from_onboard_column(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.cargo == []

    def test_cargo_cleared_when_holds_empty_after_commerce(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.cargo == []
        assert status.holds_empty == 50
        assert status.credits == 32211


class TestInfoBlockSync:
    def test_parses_info_with_cargo(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.sector_id == 178
        assert status.turns_remaining == 153
        assert status.credits == 7
        assert status.holds_total == 50
        assert status.holds_empty == 48
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.ORGANICS
        assert status.cargo[0].quantity == 2

    def test_parses_info_with_full_cargo(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.sector_id == 480
        assert status.turns_remaining == 764
        assert status.credits == 2872
        assert status.holds_total == 20
        assert status.holds_empty == 0
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20

    def test_parses_info_empty_holds(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.sector_id == 1
        assert status.turns_remaining == 282
        assert status.credits == 50219
        assert status.holds_total == 20
        assert status.holds_empty == 20
        assert status.cargo == []


class TestStatusBarSync:
    def test_parses_compact_status_bar(self, parser, mock_store):
        text = (
            " Sect 1\u2502Turns 282\u2502Creds 50,219\u2502Figs 30\u2502Shlds 0"
            "\u2502Hlds 20\u2502Ore 0\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 1
        assert status.turns_remaining == 282
        assert status.credits == 50219
        assert status.holds_total == 20
        assert status.holds_empty == 20
        assert status.cargo == []

    def test_parses_status_bar_with_cargo(self, parser, mock_store):
        text = (
            " Sect 480\u2502Turns 764\u2502Creds 2,872\u2502Figs 30\u2502Shlds 5"
            "\u2502Hlds 20\u2502Ore 20\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 480
        assert status.turns_remaining == 764
        assert status.credits == 2872
        assert status.holds_total == 20
        assert status.holds_empty == 0
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20

    def test_parses_status_bar_with_comma_in_turns(self, parser, mock_store):
        text = (
            " Sect 616\u2502Turns 1,000\u2502Creds 25\u2502Figs 1\u2502Shlds 30"
            "\u2502Hlds 1\u2502Ore 0\u2502Org 0\u2502Equ 0\u2502Col 0\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 616
        assert status.turns_remaining == 1000
        assert status.credits == 25
        assert status.holds_total == 1
        assert status.holds_empty == 1


class TestTurnCounterFormats:
    def test_stardate_turns(self, parser, mock_store):
        text = (
            "Sector  : 178 in uncharted space.\n"
            "Warps to Sector(s) :  120 - (509)\n"
            "Command [TL=00:00:00]:[178] (?=Help)? :?\n"
            "You have 816 turns this Stardate.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 816

    def test_you_have_n_turns_left(self, parser, mock_store):
        text = (
            "Sector  : 246 in uncharted space.\n"
            "Command [TL=00:00:00]:[246] (?=Help)? :P\n"
            "You have 4 turns left.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 4

    def test_no_turns_left(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[827] (?=Help)? :P\n"
            "You don't have any turns left.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 0

    def test_recover_turns(self, parser, mock_store):
        text = (
            "Sector  : 558 in Actacon (unexplored).\n"
            "Command [TL=00:00:00]:[558] (?=Help)? :N\n"
            "One turn deducted, 100 turns left.\n"
            "You recover 41 of your turns.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 141


class TestTransactionTracking:
    def test_buy_transaction_with_cost_basis(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20
        assert status.cargo[0].cost_per_unit == pytest.approx(111.0 / 20)

    def test_sell_transaction_removes_cargo(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert status.cargo == []
        assert status.holds_empty == 20

    def test_buy_then_sell_full_cycle(self, parser, mock_store):
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
        status = _last_player_status(mock_store)
        assert len(status.cargo) == 1
        assert status.cargo[0].commodity == CommodityType.FUEL_ORE
        assert status.cargo[0].quantity == 20
        assert status.cargo[0].cost_per_unit == pytest.approx(116.0 / 20)
        assert status.credits == 1623

    def test_extracts_planet(self, parser, mock_store):
        text = (
            "Sector  : 616 in uncharted space.\n"
            "Ports   : Trader Vic's, Class 6 (SBS)\n"
            "Planets : (M) Terra\n"
            "Warps to Sector(s) :  544 - 564 - 825\nCommand"
        )
        parser.execute(text)
        planet_calls = [c[0][0] for c in mock_store.upsert_planet.call_args_list]
        assert any(p.sector_id == 616 and p.name == "Terra" for p in planet_calls)

    def test_planet_associated_with_correct_sector(self, parser, mock_store):
        text = (
            "Sector  : 1 in The Federation.\n"
            "Ports   : Sol, Class 0 (Special)\n"
            "Planets : (M) Terra\n"
            "Warps to Sector(s) :  2 - 3\nCommand\n"
            "Sector  : 2 in The Federation.\n"
            "Warps to Sector(s) :  1 - 4\nCommand"
        )
        parser.execute(text)
        planet_calls = [c[0][0] for c in mock_store.upsert_planet.call_args_list]
        assert any(p.sector_id == 1 and p.name == "Terra" for p in planet_calls)
        assert not any(p.sector_id == 2 for p in planet_calls)

    def test_no_false_planet_match(self, parser, mock_store):
        text = (
            "Sector  : 50 in The Federation.\n"
            "Warps to Sector(s) :  51\nCommand"
        )
        parser.execute(text)
        mock_store.upsert_planet.assert_not_called()

    def test_planet_with_hyphenated_name(self, parser, mock_store):
        text = (
            "Sector  : 300 in uncharted space.\n"
            "Planets : (O) Mando-2\n"
            "Warps to Sector(s) :  301\nCommand"
        )
        parser.execute(text)
        planet_calls = [c[0][0] for c in mock_store.upsert_planet.call_args_list]
        assert any(p.sector_id == 300 and p.name == "Mando-2" for p in planet_calls)
