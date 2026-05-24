"""Tests for the ParseLogChunk use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.ports.game_state_writer import GameStateWriter
from tw_guidance_computer.domain.models import (
    Planet,
    PlayerStatus,
    Port,
    Sector,
    WarpConnection,
)


@pytest.fixture()
def mock_store():
    return MagicMock(spec=GameStateWriter)


@pytest.fixture()
def parser(mock_store):
    return ParseLogChunk(mock_store)


def _last_player_status(mock_store) -> PlayerStatus:
    mock_store.set_player_status.assert_called()
    return mock_store.set_player_status.call_args[0][0]


class TestCommandPrompt:
    def test_extracts_sector_from_prompt(self, parser, mock_store):
        parser.execute("Command [TL=00:00:00]:[616] (?=Help)? :")
        status = _last_player_status(mock_store)
        assert status.sector_id == 616

    def test_last_prompt_wins(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "Command [TL=00:00:00]:[200] (?=Help)? :\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 200


class TestSectorDisplay:
    def test_extracts_sector(self, parser, mock_store):
        parser.execute("Sector  : 865 in The Rovine Nebulae.\n")
        mock_store.upsert_sector.assert_any_call(
            Sector(id=865, region="The Rovine Nebulae", explored=True)
        )

    def test_extracts_port(self, parser, mock_store):
        text = (
            "Sector  : 832 in The Rovine Nebulae.\n"
            "Ports   : Nambu Minor, Class 3 (SBB)\n"
            "Warps to Sector(s) :  658\n"
        )
        parser.execute(text)
        mock_store.upsert_port.assert_any_call(
            Port(sector_id=832, name="Nambu Minor", port_class=3, port_type="SBB")
        )

    def test_extracts_planet(self, parser, mock_store):
        text = (
            "Sector  : 616 in uncharted space.\n"
            "Ports   : Trader Vic's, Class 6 (SBS)\n"
            "Planets : (M) Terra\n"
            "Warps to Sector(s) :  544 - 564 - 825\n"
        )
        parser.execute(text)
        mock_store.upsert_planet.assert_any_call(
            Planet(sector_id=616, name="Terra", planet_class="M")
        )

    def test_extracts_warps(self, parser, mock_store):
        text = "Sector  : 272 in Gastonbury.\nWarps to Sector(s) :  51 - (203) - (224) - 342 - 860\n"
        parser.execute(text)
        mock_store.replace_warps_from_sector.assert_called_once()
        call_args = mock_store.replace_warps_from_sector.call_args[0]
        assert call_args[0] == 272
        destinations = {w.to_sector for w in call_args[1]}
        assert destinations == {51, 203, 224, 342, 860}

    def test_unexplored_warps_marked(self, parser, mock_store):
        text = "Sector  : 272 in Gastonbury.\nWarps to Sector(s) :  51 - (203) - 342\n"
        parser.execute(text)
        call_args = mock_store.replace_warps_from_sector.call_args[0]
        warps = call_args[1]
        unexplored = [w for w in warps if not w.explored]
        explored = [w for w in warps if w.explored]
        assert {w.to_sector for w in unexplored} == {203}
        assert {w.to_sector for w in explored} == {51, 342}

    def test_warp_targets_upserted_as_sectors(self, parser, mock_store):
        text = "Sector  : 100 in Test.\nWarps to Sector(s) :  200 - (300)\n"
        parser.execute(text)
        mock_store.upsert_sector.assert_any_call(Sector(id=200, explored=True))
        mock_store.upsert_sector.assert_any_call(Sector(id=300, explored=False))

    def test_planet_with_hyphenated_name(self, parser, mock_store):
        text = (
            "Sector  : 300 in uncharted space.\n"
            "Planets : (O) Mando-2\n"
            "Warps to Sector(s) :  301\n"
        )
        parser.execute(text)
        mock_store.upsert_planet.assert_any_call(
            Planet(sector_id=300, name="Mando-2", planet_class="O")
        )

    def test_sets_current_sector(self, parser, mock_store):
        text = "Sector  : 500 in The Federation.\nWarps to Sector(s) :  501\n"
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 500


class TestSelfHealingWarps:
    def test_replace_warps_called_with_correct_sector(self, parser, mock_store):
        text = "Sector  : 100 in Test.\nWarps to Sector(s) :  200 - 300\n"
        parser.execute(text)
        mock_store.replace_warps_from_sector.assert_called_once_with(
            100,
            [
                WarpConnection(from_sector=100, to_sector=200, explored=True),
                WarpConnection(from_sector=100, to_sector=300, explored=True),
            ],
        )

    def test_multiple_sector_displays_each_replace(self, parser, mock_store):
        text = (
            "Sector  : 100 in Test.\n"
            "Warps to Sector(s) :  200\n"
            "Sector  : 200 in Test.\n"
            "Warps to Sector(s) :  100 - 300\n"
        )
        parser.execute(text)
        calls = mock_store.replace_warps_from_sector.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == 100
        assert calls[1][0][0] == 200


class TestNavMenuExclusion:
    def test_nav_menu_t_prefix_excluded(self, parser, mock_store):
        text = (
            "(T) Sector  : 1 in The Federation.\n"
            "    Ports   : Sol, Class 0 (Special)\n"
            "    Planets : (M) Terra\n"
            "(S) Sector  : 214 in The Federation.\n"
        )
        parser.execute(text)
        mock_store.upsert_sector.assert_not_called()
        mock_store.upsert_port.assert_not_called()
        mock_store.upsert_planet.assert_not_called()

    def test_nav_menu_digit_prefix_excluded(self, parser, mock_store):
        text = (
            "(1) Sector  : 178 (Not Scanning)\n"
            "(2) Sector  : 749 in uncharted space.\n"
            "    Ports   : Nog II, Class 2 (BSB)\n"
        )
        parser.execute(text)
        mock_store.upsert_sector.assert_not_called()
        mock_store.upsert_port.assert_not_called()

    def test_nav_menu_star_prefix_excluded(self, parser, mock_store):
        text = "(*) Sector  : 50 in The Federation.\n"
        parser.execute(text)
        mock_store.upsert_sector.assert_not_called()

    def test_real_sector_after_nav_menu_parsed(self, parser, mock_store):
        text = (
            "(T) Sector  : 1 in The Federation.\n"
            "    Ports   : Sol, Class 0 (Special)\n"
            "(S) Sector  : 214 in The Federation.\n"
            "Sector  : 272 in Gastonbury.\n"
            "Ports   : Hornet II, Class 5 (SBS)\n"
            "Warps to Sector(s) :  51 - 203\n"
        )
        parser.execute(text)
        mock_store.upsert_sector.assert_any_call(
            Sector(id=272, region="Gastonbury", explored=True)
        )
        mock_store.upsert_port.assert_any_call(
            Port(sector_id=272, name="Hornet II", port_class=5, port_type="SBS")
        )

    def test_indented_ports_under_nav_excluded(self, parser, mock_store):
        text = (
            "(2) Sector  : 749 in uncharted space.\n"
            "    Ports   : Nog II, Class 2 (BSB)\n"
            "    Planets : (M) es\n"
        )
        parser.execute(text)
        mock_store.upsert_port.assert_not_called()
        mock_store.upsert_planet.assert_not_called()


class TestTurns:
    def test_stardate_turns(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[178] (?=Help)? :\n"
            "You have 816 turns this Stardate.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 816

    def test_deducted_turns(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "One turn deducted, 809 turns left.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 809

    def test_last_turn_event_wins(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "You have 816 turns this Stardate.\n"
            "One turn deducted, 815 turns left.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.turns_remaining == 815


class TestCredits:
    def test_extracts_credits(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "You have 5,125 credits and 20 empty cargo holds.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.credits == 5125

    def test_bank_credits_ignored(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "You have 50,000 credits in your account.\n"
            "You have 1,000 credits and 20 empty cargo holds.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.credits == 1000

    def test_credits_with_commas(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "You have 1,234,567 credits and 0 empty cargo holds.\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.credits == 1234567


class TestStatusBar:
    def test_resyncs_sector_turns_credits(self, parser, mock_store):
        text = " Sect 616\u2502Turns 1,000\u2502Creds 25\n"
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 616
        assert status.turns_remaining == 1000
        assert status.credits == 25

    def test_overrides_earlier_values(self, parser, mock_store):
        text = (
            "Command [TL=00:00:00]:[100] (?=Help)? :\n"
            "You have 500 credits and 20 empty cargo holds.\n"
            " Sect 200\u2502Turns 800\u2502Creds 999\n"
        )
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.sector_id == 200
        assert status.turns_remaining == 800
        assert status.credits == 999


class TestCargoStubbed:
    def test_cargo_always_empty(self, parser, mock_store):
        text = "Command [TL=00:00:00]:[100] (?=Help)? :\n"
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.cargo == []
        assert status.holds_total == 0
        assert status.holds_empty == 0

    def test_status_bar_cargo_empty(self, parser, mock_store):
        text = " Sect 480\u2502Turns 764\u2502Creds 2,872\n"
        parser.execute(text)
        status = _last_player_status(mock_store)
        assert status.cargo == []
