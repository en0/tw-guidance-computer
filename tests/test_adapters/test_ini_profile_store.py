import configparser
import os
import stat

import pytest

from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore
from tw_guidance_computer.domain.exceptions import ConfigError, ProfileExistsError, ProfileNotFoundError
from tw_guidance_computer.domain.models import Profile


@pytest.fixture()
def config_path(tmp_path):
    return tmp_path / "config" / "tw.ini"


@pytest.fixture()
def store(config_path):
    return IniProfileStore(config_path)


class TestEnsureConfigExists:
    def test_creates_default_config(self, store, config_path):
        store.ensure_config_exists()

        assert config_path.exists()
        cfg = configparser.ConfigParser()
        cfg.read(str(config_path))
        assert cfg.has_section("profile:default")
        assert cfg.get("profile:default", "db") == "~/.local/share/tw-guidance-computer/game.db"
        assert cfg.defaults()["default_profile"] == "default"
        mode = stat.S_IMODE(config_path.stat().st_mode)
        assert mode == 0o600

    def test_noop_if_file_exists(self, store, config_path):
        config_path.parent.mkdir(parents=True)
        config_path.write_text("[profile:custom]\ndb = /tmp/custom.db\n")

        store.ensure_config_exists()

        content = config_path.read_text()
        assert "custom" in content
        assert "default" not in content


class TestGetProfile:
    def test_returns_profile_with_expanded_path(self, store, config_path):
        store.ensure_config_exists()

        profile = store.get_profile("default")

        assert profile.name == "default"
        assert profile.db_path == os.path.expanduser("~/.local/share/tw-guidance-computer/game.db")

    def test_raises_profile_not_found(self, store, config_path):
        store.ensure_config_exists()

        with pytest.raises(ProfileNotFoundError, match="nonexistent"):
            store.get_profile("nonexistent")


class TestListProfiles:
    def test_returns_all_profiles_with_default(self, store, config_path):
        store.ensure_config_exists()

        listing = store.list_profiles()

        assert listing.default_name == "default"
        assert len(listing.profiles) == 1
        assert listing.profiles[0].name == "default"

    def test_multiple_profiles(self, store, config_path):
        store.ensure_config_exists()
        store.save_profile(Profile(name="second", db_path="~/.local/share/tw-guidance-computer/second.db"))

        listing = store.list_profiles()

        names = [p.name for p in listing.profiles]
        assert "default" in names
        assert "second" in names


class TestSaveProfile:
    def test_writes_new_section(self, store, config_path):
        store.ensure_config_exists()
        profile = Profile(name="test", db_path="/tmp/test.db")

        store.save_profile(profile)

        cfg = configparser.ConfigParser()
        cfg.read(str(config_path))
        assert cfg.has_section("profile:test")
        assert cfg.get("profile:test", "db") == "/tmp/test.db"

    def test_raises_profile_exists_for_duplicate(self, store, config_path):
        store.ensure_config_exists()

        with pytest.raises(ProfileExistsError, match="default"):
            store.save_profile(Profile(name="default", db_path="/tmp/dup.db"))


class TestResolveDefaultDbPath:
    def test_default_profile(self, store):
        assert store.resolve_default_db_path("default") == "~/.local/share/tw-guidance-computer/game.db"

    def test_named_profile(self, store):
        assert store.resolve_default_db_path("myserver") == "~/.local/share/tw-guidance-computer/myserver.db"


class TestConfigError:
    def test_malformed_config_raises(self, store, config_path):
        config_path.parent.mkdir(parents=True)
        config_path.write_text("[profile:bad\nno closing bracket")

        with pytest.raises(ConfigError):
            store.get_profile("bad")


class TestGetConfigValue:
    def test_reads_from_profile_section(self, store, config_path):
        config_path.parent.mkdir(parents=True)
        config_path.write_text("[DEFAULT]\nfoo = default_val\n\n[profile:myprof]\nfoo = profile_val\n")

        result = store.get_config_value("myprof", "foo", "fallback")

        assert result == "profile_val"

    def test_falls_back_to_default_section(self, store, config_path):
        store.ensure_config_exists()

        result = store.get_config_value("default", "turn_warning_yellow", "999")

        assert result == "200"

    def test_falls_back_to_provided_default(self, store, config_path):
        store.ensure_config_exists()

        result = store.get_config_value("default", "nonexistent_key", "my_fallback")

        assert result == "my_fallback"
