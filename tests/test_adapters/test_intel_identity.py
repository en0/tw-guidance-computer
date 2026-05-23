import hashlib

import pytest

from tw_guidance_computer.adapters.outbound.intel_identity import (
    compute_intel_identity,
    validate_intel_config,
)
from tw_guidance_computer.domain.exceptions import IntelKeyError
from tw_guidance_computer.domain.models import IntelConfig


class TestComputeIntelIdentity:
    def test_computes_sha256_of_pubkey(self, tmp_path):
        key_path = str(tmp_path / "id_ed25519")
        pub_content = b"ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@host\n"
        (tmp_path / "id_ed25519.pub").write_bytes(pub_content)
        result = compute_intel_identity(key_path)
        expected = hashlib.sha256(pub_content).hexdigest()
        assert result == expected

    def test_raises_on_missing_pubkey(self, tmp_path):
        key_path = str(tmp_path / "id_ed25519")
        with pytest.raises(IntelKeyError, match="Public key not found"):
            compute_intel_identity(key_path)

    def test_different_keys_produce_different_hashes(self, tmp_path):
        key1 = str(tmp_path / "key1")
        key2 = str(tmp_path / "key2")
        (tmp_path / "key1.pub").write_bytes(b"ssh-ed25519 AAAA1 user@host1\n")
        (tmp_path / "key2.pub").write_bytes(b"ssh-ed25519 AAAA2 user@host2\n")
        assert compute_intel_identity(key1) != compute_intel_identity(key2)


class TestValidateIntelConfig:
    def test_passes_when_both_files_exist(self, tmp_path):
        key_path = str(tmp_path / "id_ed25519")
        (tmp_path / "id_ed25519").write_text("private key")
        (tmp_path / "id_ed25519.pub").write_text("public key")
        config = IntelConfig(host="intel.example.com", key_path=key_path)
        validate_intel_config(config)

    def test_raises_on_missing_private_key(self, tmp_path):
        key_path = str(tmp_path / "id_ed25519")
        (tmp_path / "id_ed25519.pub").write_text("public key")
        config = IntelConfig(host="intel.example.com", key_path=key_path)
        with pytest.raises(IntelKeyError, match="Private key not found"):
            validate_intel_config(config)

    def test_raises_on_missing_public_key(self, tmp_path):
        key_path = str(tmp_path / "id_ed25519")
        (tmp_path / "id_ed25519").write_text("private key")
        config = IntelConfig(host="intel.example.com", key_path=key_path)
        with pytest.raises(IntelKeyError, match="Public key not found"):
            validate_intel_config(config)
