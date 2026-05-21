"""Integration tests for profile resolution in the composition root."""

from pathlib import Path

import pytest

from tw_guidance_computer.compose import AppContext
from tw_guidance_computer.domain.exceptions import DatabaseNotFoundError, ProfileNotFoundError, ValidationError
from tw_guidance_computer.domain.models import TurnThresholds


class TestAppContextResolution:
    def test_creates_config_and_resolves_default(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        assert not config_path.exists()

        ctx = AppContext(config_path=config_path)
        try:
            assert config_path.exists()
            assert ctx.thresholds == TurnThresholds(yellow=200, red=100, alert=50)
        finally:
            ctx.close()

    def test_with_named_profile(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n\n"
            "[profile:alpha]\n"
            f"db = {tmp_path / 'alpha.db'}\n"
        )

        ctx = AppContext(profile_name="alpha", config_path=config_path)
        try:
            # Verify it resolved the alpha profile (store was created at alpha path)
            assert ctx.store is not None
        finally:
            ctx.close()

    def test_missing_profile_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            "db = ~/.local/share/tw-guidance-computer/game.db\n"
        )

        with pytest.raises(ProfileNotFoundError, match="nonexistent"):
            AppContext(profile_name="nonexistent", config_path=config_path)

    def test_reads_custom_thresholds(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            "turn_warning_yellow = 300\n"
            "turn_warning_red = 150\n"
            "turn_alert_threshold = 75\n"
        )

        ctx = AppContext(config_path=config_path)
        try:
            assert ctx.thresholds == TurnThresholds(yellow=300, red=150, alert=75)
        finally:
            ctx.close()

    def test_invalid_thresholds_raise_validation_error(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            "turn_warning_yellow = 50\n"
            "turn_warning_red = 100\n"
            "turn_alert_threshold = 200\n"
        )

        with pytest.raises(ValidationError):
            AppContext(config_path=config_path)

    def test_require_existing_db_raises_when_missing(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'nonexistent' / 'game.db'}\n"
        )

        with pytest.raises(DatabaseNotFoundError, match="No database found"):
            AppContext(config_path=config_path, require_existing_db=True)

    def test_require_existing_db_succeeds_when_present(self, tmp_path: Path) -> None:
        db_path = tmp_path / "game.db"
        db_path.touch()
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {db_path}\n"
        )

        ctx = AppContext(config_path=config_path, require_existing_db=True)
        try:
            assert ctx.store is not None
        finally:
            ctx.close()
