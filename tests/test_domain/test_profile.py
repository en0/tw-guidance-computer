from __future__ import annotations

import pytest

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models.profile import Profile, ProfileListing


class TestProfile:
    def test_valid_simple_name(self):
        p = Profile(name="myserver", db_path="/some/path.db")
        assert p.name == "myserver"
        assert p.db_path == "/some/path.db"

    def test_valid_name_with_hyphens(self):
        p = Profile(name="my-server-1", db_path="/db")
        assert p.name == "my-server-1"

    def test_valid_default_name(self):
        p = Profile(name="default", db_path="/db")
        assert p.name == "default"

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError, match="must not be empty"):
            Profile(name="", db_path="/db")

    def test_name_with_spaces_raises(self):
        with pytest.raises(ValidationError, match="lowercase letters, digits, and hyphens"):
            Profile(name="my server", db_path="/db")

    def test_name_with_uppercase_raises(self):
        with pytest.raises(ValidationError, match="lowercase letters, digits, and hyphens"):
            Profile(name="MyServer", db_path="/db")

    def test_name_with_special_chars_raises(self):
        with pytest.raises(ValidationError, match="lowercase letters, digits, and hyphens"):
            Profile(name="my_server!", db_path="/db")

    def test_name_starting_with_hyphen_raises(self):
        with pytest.raises(ValidationError, match="must not start or end with a hyphen"):
            Profile(name="-bad", db_path="/db")

    def test_name_ending_with_hyphen_raises(self):
        with pytest.raises(ValidationError, match="must not start or end with a hyphen"):
            Profile(name="bad-", db_path="/db")

    def test_name_over_64_chars_raises(self):
        with pytest.raises(ValidationError, match="64 characters or fewer"):
            Profile(name="a" * 65, db_path="/db")

    def test_name_exactly_64_chars_valid(self):
        p = Profile(name="a" * 64, db_path="/db")
        assert len(p.name) == 64


class TestProfileListing:
    def test_default_profile_returns_match(self):
        p = Profile(name="myserver", db_path="/db/myserver.db")
        listing = ProfileListing(profiles=[p], default_name="myserver")
        assert listing.default_profile is p

    def test_default_profile_returns_none_when_no_match(self):
        p = Profile(name="other", db_path="/db/other.db")
        listing = ProfileListing(profiles=[p], default_name="missing")
        assert listing.default_profile is None

    def test_empty_default_name_raises(self):
        with pytest.raises(ValidationError, match="default_name must not be empty"):
            ProfileListing(profiles=[], default_name="")
