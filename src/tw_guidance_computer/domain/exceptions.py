"""Domain exceptions for the TW Guidance Computer."""


class GuidanceError(Exception):
    """Base exception for all guidance computer errors."""


class ParseError(GuidanceError):
    """Raised when log parsing encounters unrecoverable input."""


class PathNotFoundError(GuidanceError):
    """Raised when no path exists between two sectors."""


class SectorNotFoundError(GuidanceError):
    """Raised when a sector is not in the knowledge base."""
