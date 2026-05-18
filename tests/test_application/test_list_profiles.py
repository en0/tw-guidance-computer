from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.list_profiles import ListProfiles
from tw_guidance_computer.application.ports.profile_store import ProfileStore
from tw_guidance_computer.domain.models import Profile, ProfileListing


@pytest.fixture()
def mock_store():
    return MagicMock(spec=ProfileStore)


@pytest.fixture()
def list_profiles(mock_store):
    return ListProfiles(mock_store)


class TestListProfiles:
    def test_returns_profile_listing_from_store(self, list_profiles, mock_store):
        expected = ProfileListing(
            profiles=[Profile(name="default", db_path="/tmp/game.db")],
            default_name="default",
        )
        mock_store.list_profiles.return_value = expected

        result = list_profiles.execute()

        assert result is expected

    def test_delegates_to_store(self, list_profiles, mock_store):
        mock_store.list_profiles.return_value = ProfileListing(
            profiles=[], default_name="main"
        )

        _ = list_profiles.execute()

        mock_store.list_profiles.assert_called_once()
