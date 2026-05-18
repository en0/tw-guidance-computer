"""Use case: list all configured profiles."""

from typing import final

from tw_guidance_computer.application.ports.profile_store import ProfileStore
from tw_guidance_computer.domain.models import ProfileListing


@final
class ListProfiles:
    """List all configured profiles with the default selection."""

    def __init__(self, store: ProfileStore) -> None:
        """Initialize with a profile store.

        Args:
            store: The profile configuration store.
        """
        self._store = store

    def execute(self) -> ProfileListing:
        """List all profiles.

        Returns:
            A listing of all profiles and the default name.
        """
        return self._store.list_profiles()
