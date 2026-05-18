"""Tests for the CreateProfile use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.create_profile import CreateProfile
from tw_guidance_computer.application.ports.profile_store import ProfileStore
from tw_guidance_computer.domain.exceptions import ProfileExistsError, ValidationError


@pytest.fixture()
def mock_store():
    store = MagicMock(spec=ProfileStore)
    store.resolve_default_db_path.return_value = "/home/user/.local/share/tw-guidance-computer/test-game.db"
    return store


@pytest.fixture()
def create_profile(mock_store):
    return CreateProfile(mock_store)


class TestCreateProfile:
    def test_happy_path(self, create_profile, mock_store):
        profile = create_profile.execute("test-game")

        assert profile.name == "test-game"
        assert profile.db_path == "/home/user/.local/share/tw-guidance-computer/test-game.db"
        mock_store.resolve_default_db_path.assert_called_once_with("test-game")
        mock_store.save_profile.assert_called_once_with(profile)

    def test_duplicate_name_raises(self, create_profile, mock_store):
        mock_store.save_profile.side_effect = ProfileExistsError("already exists")

        with pytest.raises(ProfileExistsError, match="already exists"):
            create_profile.execute("test-game")

    def test_invalid_name_raises(self, create_profile):
        with pytest.raises(ValidationError, match="must contain only lowercase"):
            create_profile.execute("INVALID NAME!")
