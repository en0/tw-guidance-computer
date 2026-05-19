"""Integration tests for profile resolution in the composition root."""

from pathlib import Path

import pytest

from tw_guidance_computer.compose import resolve_config, resolve_db_path
from tw_guidance_computer.domain.exceptions import ProfileNotFoundError, ValidationError
from tw_guidance_computer.domain.models import TurnThresholds


class TestResolveDbPath:
    def test_creates_config_and_returns_default(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        assert not config_path.exists()

        db_path = resolve_db_path(None, config_path=config_path)

        assert config_path.exists()
        assert db_path == Path.home() / ".local" / "share" / "tw-guidance-computer" / "game.db"

    def test_with_named_profile(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n\n"
            "[profile:alpha]\n"
            "db = ~/.local/share/tw-guidance-computer/alpha.db\n"
        )

        db_path = resolve_db_path("alpha", config_path=config_path)

        assert db_path == Path.home() / ".local" / "share" / "tw-guidance-computer" / "alpha.db"

    def test_missing_profile_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n"
        )

        with pytest.raises(ProfileNotFoundError, match="nonexistent"):
            resolve_db_path("nonexistent", config_path=config_path)


class TestResolveConfig:
    def test_returns_default_thresholds(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"

        db_path, thresholds = resolve_config(None, config_path=config_path)

        assert db_path == Path.home() / ".local" / "share" / "tw-guidance-computer" / "game.db"
        assert thresholds == TurnThresholds(yellow=200, red=100, alert=50)

    def test_reads_custom_thresholds(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n"
            "turn_warning_yellow = 300\n"
            "turn_warning_red = 150\n"
            "turn_alert_threshold = 75\n"
        )

        _, thresholds = resolve_config(None, config_path=config_path)

        assert thresholds == TurnThresholds(yellow=300, red=150, alert=75)

    def test_invalid_thresholds_raise_validation_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n"
            "turn_warning_yellow = 50\n"
            "turn_warning_red = 100\n"
            "turn_alert_threshold = 200\n"
        )

        with pytest.raises(ValidationError):
            resolve_config(None, config_path=config_path)
