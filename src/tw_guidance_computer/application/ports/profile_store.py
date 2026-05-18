"""Port for profile configuration storage."""

from typing import Protocol

from tw_guidance_computer.domain.models import Profile, ProfileListing


class ProfileStore(Protocol):
    """Abstraction over the profile config file.

    Manages named profiles that map to game databases.
    """

    def get_profile(self, name: str) -> Profile:
        """Retrieve a profile by name.

        Args:
            name: The profile name to look up.

        Returns:
            The matching profile.

        Raises:
            ProfileNotFoundError: If no profile with that name exists.
            ConfigError: If the config file is malformed or unreadable.
        """
        ...

    def list_profiles(self) -> ProfileListing:
        """List all profiles with the default selection.

        Returns:
            A listing of all profiles and the default name.

        Raises:
            ConfigError: If the config file is malformed or unreadable.
        """
        ...

    def save_profile(self, profile: Profile) -> None:
        """Save a new profile to the config.

        Args:
            profile: The profile to save.

        Raises:
            ProfileExistsError: If a profile with that name already exists.
            ConfigError: If the config file is malformed or unwritable.
        """
        ...

    def ensure_config_exists(self) -> None:
        """Create the config file with a default profile if missing.

        No-op if the config file already exists.

        Raises:
            ConfigError: If the config file cannot be created.
        """
        ...

    def resolve_default_db_path(self, name: str) -> str:
        """Generate the conventional database path for a profile name.

        Args:
            name: The profile name.

        Returns:
            The default database file path string for this profile.
        """
        ...
