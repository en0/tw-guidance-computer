"""Domain exceptions for the TW Guidance Computer."""


class GuidanceError(Exception):
    """Base exception for all guidance computer errors."""


class ParseError(GuidanceError):
    """Raised when log parsing encounters unrecoverable input."""


class PathNotFoundError(GuidanceError):
    """Raised when no path exists between two sectors."""


class SectorNotFoundError(GuidanceError):
    """Raised when a sector is not in the knowledge base."""


class ValidationError(GuidanceError):
    """Raised when a domain object cannot be constructed with invalid data."""


class StorageError(GuidanceError):
    """Raised when persistent storage is unavailable or fails."""


class DatabaseNotFoundError(GuidanceError):
    """Raised when the database file does not exist and is required."""


class LogReadError(GuidanceError):
    """Raised when reading the session log fails."""


class ProfileNotFoundError(GuidanceError):
    """Raised when a profile is not in the config."""


class ProfileExistsError(GuidanceError):
    """Raised when trying to create a profile that already exists."""


class ConfigError(GuidanceError):
    """Raised when the config file is malformed or unreadable."""


class IntelError(GuidanceError):
    """Base exception for all intel sync errors."""


class IntelConnectError(IntelError):
    """Raised when connection or authentication to the intel server fails."""


class IntelTransferError(IntelError):
    """Raised when reading or writing files on the intel server fails."""


class IntelDataError(IntelError):
    """Raised when intel data is corrupt or invalid."""


class IntelKeyError(IntelError):
    """Raised when the SSH key file is inaccessible."""
