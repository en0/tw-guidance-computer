"""Domain model: sectors and warp connections."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Sector:
    """A sector in the TW2002 universe."""

    id: int
    region: str = ""
    explored: bool = False

    def __post_init__(self) -> None:
        """Validate sector fields."""
        if self.id < 1:
            raise ValidationError("sector id must be positive")


@dataclass(frozen=True)
class WarpConnection:
    """A warp lane between two sectors."""

    from_sector: int
    to_sector: int
    explored: bool = True

    def __post_init__(self) -> None:
        """Validate warp connection fields."""
        if self.from_sector < 1:
            raise ValidationError("from_sector must be positive")
        if self.to_sector < 1:
            raise ValidationError("to_sector must be positive")
