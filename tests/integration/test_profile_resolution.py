"""Integration tests for profile resolution in the composition root."""

from pathlib import Path

import pytest

from tw_guidance_computer.compose import resolve_db_path
from tw_guidance_computer.domain.exceptions import ProfileNotFoundError


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
