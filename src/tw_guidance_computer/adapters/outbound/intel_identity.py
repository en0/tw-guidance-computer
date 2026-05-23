"""Intel identity utility — computes player identity from SSH public key."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tw_guidance_computer.domain.exceptions import IntelKeyError
from tw_guidance_computer.domain.models import IntelConfig


def compute_intel_identity(key_path: str) -> str:
    """Compute player identity hash from SSH public key.

    Args:
        key_path: Path to the private key (reads key_path + ".pub").

    Returns:
        SHA-256 hex hash of the public key file content.

    Raises:
        IntelKeyError: If the .pub file does not exist.
    """
    pub_path = Path(key_path + ".pub")
    if not pub_path.exists():
        raise IntelKeyError(f"Public key not found: {pub_path}")
    content = pub_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def validate_intel_config(config: IntelConfig) -> None:
    """Validate that key files referenced by config exist on disk.

    Args:
        config: Intel configuration with key_path.

    Raises:
        IntelKeyError: If private key or public key file is missing.
    """
    private_path = Path(config.key_path)
    if not private_path.exists():
        raise IntelKeyError(f"Private key not found: {private_path}")
    pub_path = Path(config.key_path + ".pub")
    if not pub_path.exists():
        raise IntelKeyError(f"Public key not found: {pub_path}")
