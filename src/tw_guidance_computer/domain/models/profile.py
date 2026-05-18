"""Domain model: profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tw_guidance_computer.domain.exceptions import ValidationError

_NAME_RE = re.compile(r"^[a-z0-9-]+$")


@dataclass(frozen=True)
class Profile:
    """A named game profile with a storage location."""

    name: str
    db_path: str

    def __post_init__(self) -> None:
        """Validate profile fields."""
        if not self.name:
            raise ValidationError("name must not be empty")
        if len(self.name) > 64:
            raise ValidationError("name must be 64 characters or fewer")
        if not _NAME_RE.match(self.name):
            raise ValidationError("name must contain only lowercase letters, digits, and hyphens")
        if self.name.startswith("-") or self.name.endswith("-"):
            raise ValidationError("name must not start or end with a hyphen")


@dataclass(frozen=True)
class ProfileListing:
    """A listing of all profiles with the default selection."""

    profiles: list[Profile] = field(default_factory=list)
    default_name: str = ""

    def __post_init__(self) -> None:
        """Validate profile listing fields."""
        if not self.default_name:
            raise ValidationError("default_name must not be empty")

    @property
    def default_profile(self) -> Profile | None:
        """Find the profile matching default_name, or None if not found."""
        for p in self.profiles:
            if p.name == self.default_name:
                return p
        return None
