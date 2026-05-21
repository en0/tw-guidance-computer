"""Tests for HUD TUI adapter run() dispatch."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.inbound.tui import HudDisplay
from tw_guidance_computer.domain.exceptions import ProfileExistsError
from tw_guidance_computer.domain.models import TurnThresholds


@pytest.fixture()
def mock_use_cases():
    return MagicMock()


@pytest.fixture()
def mock_reader():
    return MagicMock()


@pytest.fixture()
def mock_close():
    return MagicMock()


@pytest.fixture()
def mock_hud_context_factory(mock_use_cases, mock_reader, mock_close):
    return MagicMock(return_value=(mock_use_cases, mock_reader, TurnThresholds(), mock_close))


@pytest.fixture()
def mock_create_profile():
    return MagicMock()


@pytest.fixture()
def hud(mock_create_profile, mock_hud_context_factory):
    return HudDisplay(
        create_profile=mock_create_profile,
        hud_context_factory=mock_hud_context_factory,
    )


class TestHudRun:
    def test_calls_factory_with_parsed_args(self, hud, mock_hud_context_factory, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        hud.run(argv=[str(logfile), "-p", "myprofile", "--parse-existing"])
        mock_hud_context_factory.assert_called_once_with("myprofile", logfile, True)

    def test_calls_factory_defaults(self, hud, mock_hud_context_factory, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        hud.run(argv=[str(logfile)])
        mock_hud_context_factory.assert_called_once_with(None, logfile, False)

    def test_close_fn_called_after_curses(self, hud, mock_close, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        hud.run(argv=[str(logfile)])
        mock_close.assert_called_once()

    def test_close_fn_called_on_curses_error(self, hud, mock_close, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", MagicMock(side_effect=RuntimeError("curses boom")))
        with pytest.raises(RuntimeError, match="curses boom"):
            hud.run(argv=[str(logfile)])
        mock_close.assert_called_once()

    def test_missing_logfile_exits(self, hud, tmp_path):
        with pytest.raises(SystemExit):
            hud.run(argv=[str(tmp_path / "nonexistent.log")])


class TestHudCreateProfile:
    def test_create_profile_called(self, hud, mock_create_profile, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        mock_create_profile.execute.return_value = MagicMock(name="test", db_path="/tmp/t.db")
        hud.run(argv=[str(logfile), "-p", "test", "--create"])
        mock_create_profile.execute.assert_called_once_with("test")

    def test_create_without_profile_skips(self, hud, mock_create_profile, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        hud.run(argv=[str(logfile), "--create"])
        mock_create_profile.execute.assert_not_called()

    def test_profile_exists_silently_passes(self, hud, mock_create_profile, tmp_path, monkeypatch):
        logfile = tmp_path / "session.log"
        logfile.write_text("data")
        monkeypatch.setattr("curses.wrapper", lambda fn: None)
        mock_create_profile.execute.side_effect = ProfileExistsError("exists")
        hud.run(argv=[str(logfile), "-p", "test", "--create"])
        # Should not raise — silently passes
