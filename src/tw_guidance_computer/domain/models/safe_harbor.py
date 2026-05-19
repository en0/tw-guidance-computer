"""Domain models: safe harbor routing."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class SafeHarborRoute:
    """A route to a safe harbor destination."""

    destination_sector: int
    destination_name: str
    route: list[int]

    def __post_init__(self) -> None:
        """Validate safe harbor route fields."""
        if self.destination_sector < 1:
            raise ValidationError("destination_sector must be positive")
        if not self.route:
            raise ValidationError("route must not be empty")

    @property
    def hops(self) -> int:
        """Number of hops to reach the destination."""
        return len(self.route) - 1


@dataclass(frozen=True)
class TurnThresholds:
    """Turn count thresholds for warning escalation."""

    yellow: int = 200
    red: int = 100
    alert: int = 50

    def __post_init__(self) -> None:
        """Validate turn threshold fields."""
        if self.yellow < 1:
            raise ValidationError("yellow must be positive")
        if self.red < 1:
            raise ValidationError("red must be positive")
        if self.alert < 1:
            raise ValidationError("alert must be positive")
        if not (self.yellow > self.red > self.alert):
            raise ValidationError("must satisfy yellow > red > alert")
