"""Domain models: shared intel sync."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class IntelConfig:
    """Connection and sync configuration for the intel server."""

    host: str
    key_path: str
    port: int = 22
    sync_interval: int = 300
    sync_budget: int = 30
    max_file_size: int = 10485760

    def __post_init__(self) -> None:
        """Validate intel config fields."""
        if not self.host.strip():
            raise ValidationError("host must not be empty")
        if not 1 <= self.port <= 65535:
            raise ValidationError("port must be 1-65535")
        if self.sync_budget >= self.sync_interval:
            raise ValidationError("sync_budget must be less than sync_interval")
        if self.max_file_size <= 0:
            raise ValidationError("max_file_size must be positive")


@dataclass(frozen=True)
class RemoteFile:
    """An SFTP file listing entry."""

    name: str
    size: int

    def __post_init__(self) -> None:
        """Validate remote file fields."""
        if not self.name.strip():
            raise ValidationError("name must not be empty")
        if self.size < 0:
            raise ValidationError("size must be non-negative")


@dataclass(frozen=True)
class IntelMergeResult:
    """Import statistics from merging intel data."""

    sectors_added: int = 0
    ports_added: int = 0
    ports_updated: int = 0
    warps_added: int = 0
    planets_added: int = 0

    def __post_init__(self) -> None:
        """Validate merge result fields."""
        for field_name in ("sectors_added", "ports_added", "ports_updated", "warps_added", "planets_added"):
            if getattr(self, field_name) < 0:
                raise ValidationError(f"{field_name} must be non-negative")

    @property
    def total(self) -> int:
        """Total number of records affected."""
        return (
            self.sectors_added
            + self.ports_added
            + self.ports_updated
            + self.warps_added
            + self.planets_added
        )


@dataclass(frozen=True)
class SyncStatus:
    """Worker state for HUD communication."""

    last_error: str | None = None
    shutdown_status: str | None = None

    def __post_init__(self) -> None:
        """Validate sync status fields."""
        if self.last_error is not None and not self.last_error.strip():
            raise ValidationError("last_error must not be empty if set")
