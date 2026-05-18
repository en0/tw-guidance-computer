"""Use case: create a new game profile."""

from __future__ import annotations

from typing import final

from tw_guidance_computer.application.ports.profile_store import ProfileStore
from tw_guidance_computer.domain.models import Profile


@final
class CreateProfile:
    """Create a named profile with a default database path.

    Delegates path resolution and persistence to the profile store.
    Domain validation occurs during Profile construction.
    """

    def __init__(self, store: ProfileStore) -> None:
        """Initialize with a profile store.

        Args:
            store: The profile configuration store.
        """
        self._store = store

    def execute(self, name: str) -> Profile:
        """Create and persist a new profile.

        Args:
            name: The profile name (validated by Profile domain model).

        Returns:
            The newly created Profile.

        Raises:
            ValidationError: If the name is invalid.
            ProfileExistsError: If a profile with that name already exists.
        """
        db_path = self._store.resolve_default_db_path(name)
        profile = Profile(name=name, db_path=db_path)
        self._store.save_profile(profile)
        return profile
