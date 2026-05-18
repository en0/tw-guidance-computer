"""Domain model: planets."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Planet:
    """A planet in a sector."""

    sector_id: int
    name: str
    planet_class: str

    def __post_init__(self) -> None:
        """Validate planet fields."""
        if self.sector_id < 1:
            raise ValidationError("sector_id must be positive")
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if len(self.planet_class) != 1 or not self.planet_class.isupper():
            raise ValidationError("planet_class must be a single uppercase letter")
