"""Domain model: chat messages."""

from __future__ import annotations

from dataclasses import dataclass

from tw_guidance_computer.domain.exceptions import ValidationError


@dataclass(frozen=True)
class ChatMessage:
    """A chat message from sub-space radio or fed comm-link."""

    sender: str
    message: str
    channel: str
    timestamp: str = ""

    def __post_init__(self) -> None:
        """Validate chat message fields."""
        if not self.sender.strip():
            raise ValidationError("sender must not be empty")
        if not self.message.strip():
            raise ValidationError("message must not be empty")
        if not self.channel.strip():
            raise ValidationError("channel must not be empty")
