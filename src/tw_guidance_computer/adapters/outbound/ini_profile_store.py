"""INI-based implementation of the ProfileStore port."""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.profile_store import ProfileStore
from tw_guidance_computer.domain.exceptions import ConfigError, ProfileExistsError, ProfileNotFoundError
from tw_guidance_computer.domain.models import Profile, ProfileListing

_DEFAULT_CONFIG = """\
[DEFAULT]
default_profile = default
turn_warning_yellow = 200
turn_warning_red = 100
turn_alert_threshold = 50

[profile:default]
db = ~/.local/share/tw-guidance-computer/game.db
"""

_SECTION_PREFIX = "profile:"


@final
class IniProfileStore(ProfileStore):
    """Manages profiles via an INI config file."""

    def __init__(self, config_path: Path) -> None:
        """Initialize with the path to the config file.

        Args:
            config_path: Path to the INI config file.
        """
        self._config_path = config_path

    @override
    def ensure_config_exists(self) -> None:
        """Create the config file with a default profile if missing."""
        if self._config_path.exists():
            return
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(_DEFAULT_CONFIG)
            self._config_path.chmod(0o600)
        except OSError as e:
            raise ConfigError(str(e)) from e

    @override
    def resolve_default_db_path(self, name: str) -> str:
        """Generate the conventional database path for a profile name."""
        if name == "default":
            return "~/.local/share/tw-guidance-computer/game.db"
        return f"~/.local/share/tw-guidance-computer/{name}.db"

    @override
    def get_profile(self, name: str) -> Profile:
        """Retrieve a profile by name."""
        cfg = self._read_config()
        section = f"{_SECTION_PREFIX}{name}"
        if not cfg.has_section(section):
            raise ProfileNotFoundError(f"Profile not found: {name}")
        db_path = os.path.expanduser(cfg.get(section, "db"))
        return Profile(name=name, db_path=db_path)

    @override
    def list_profiles(self) -> ProfileListing:
        """List all profiles with the default selection."""
        cfg = self._read_config()
        profiles: list[Profile] = []
        for section in cfg.sections():
            if section.startswith(_SECTION_PREFIX):
                name = section[len(_SECTION_PREFIX):]
                db_path = os.path.expanduser(cfg.get(section, "db"))
                profiles.append(Profile(name=name, db_path=db_path))
        default_name = cfg.defaults().get("default_profile", "default")
        return ProfileListing(profiles=profiles, default_name=default_name)

    @override
    def save_profile(self, profile: Profile) -> None:
        """Save a new profile to the config."""
        cfg = self._read_config()
        section = f"{_SECTION_PREFIX}{profile.name}"
        if cfg.has_section(section):
            raise ProfileExistsError(f"Profile already exists: {profile.name}")
        try:
            cfg.add_section(section)
            cfg.set(section, "db", profile.db_path)
            with self._config_path.open("w") as f:
                cfg.write(f)
        except configparser.Error as e:
            raise ConfigError(str(e)) from e

    def get_config_value(self, profile_name: str, key: str, default: str) -> str:
        """Read a config value from a profile section with DEFAULT fallback.

        Reads from [profile:{profile_name}] section. Falls back to [DEFAULT]
        section via configparser's built-in cascade. If key not found anywhere,
        returns the provided default.

        Args:
            profile_name: The profile section to read from.
            key: The config key to look up.
            default: Value to return if key not found.

        Returns:
            The config value as a string.
        """
        cfg = self._read_config()
        section = f"{_SECTION_PREFIX}{profile_name}"
        return cfg.get(section, key, fallback=default)

    def _read_config(self) -> configparser.ConfigParser:
        """Read and return the config parser instance."""
        cfg = configparser.ConfigParser()
        try:
            cfg.read(str(self._config_path))
        except configparser.Error as e:
            raise ConfigError(str(e)) from e
        return cfg
