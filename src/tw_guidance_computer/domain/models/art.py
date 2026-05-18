"""Domain model: sector art rendering types."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class ArtCell:
    """A single cell in a rendered sector art grid."""

    char: str
    color: str

    def __post_init__(self) -> None:
        """Validate art cell fields."""
        if len(self.char) != 1:
            raise ValidationError("char must be exactly one character")
