"""Integration tests for intel wiring in the composition root."""

from pathlib import Path

import pytest

from tw_guidance_computer.compose import AppContext, build_cli
from tw_guidance_computer.domain.exceptions import IntelKeyError


class TestIntelWiringDisabled:
    def test_no_intel_when_host_not_configured(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
        )

        ctx = AppContext(config_path=config_path)
        try:
            assert ctx.sync_worker is None
            assert ctx.push_intel is None
            assert ctx.pull_intel is None
            assert ctx.intel_config is None
        finally:
            ctx.close()

    def test_cli_intel_none_when_not_configured(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
        )

        cli = build_cli(config_path=config_path)
        assert cli._intel_context_factory is not None
        push, pull, config, store = cli._intel_context_factory(None)
        assert push is None
        assert pull is None
        assert config is None


class TestIntelWiringEnabled:
    def test_intel_constructed_when_configured(self, tmp_path: Path) -> None:
        # Create key files
        key_path = tmp_path / "intel_key"
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----\n")  # nosec
        pub_path = tmp_path / "intel_key.pub"
        pub_path.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake test@host\n")

        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            f"intel_host = intel.example.com\n"
            f"intel_key = {key_path}\n"
            f"intel_port = 2222\n"
        )

        ctx = AppContext(config_path=config_path)
        try:
            assert ctx.sync_worker is not None
            assert ctx.push_intel is not None
            assert ctx.pull_intel is not None
            assert ctx.intel_config is not None
            assert ctx.intel_config.host == "intel.example.com"
            assert ctx.intel_config.port == 2222
        finally:
            ctx.close()

    def test_cli_intel_constructed_when_db_exists(self, tmp_path: Path) -> None:
        # Create key files
        key_path = tmp_path / "intel_key"
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----\n")  # nosec
        pub_path = tmp_path / "intel_key.pub"
        pub_path.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake test@host\n")

        db_path = tmp_path / "game.db"
        db_path.touch()

        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {db_path}\n"
            f"intel_host = intel.example.com\n"
            f"intel_key = {key_path}\n"
        )

        cli = build_cli(config_path=config_path)
        assert cli._intel_context_factory is not None
        push, pull, config, store = cli._intel_context_factory(None)
        assert push is not None
        assert pull is not None
        assert config is not None

    def test_cli_intel_none_when_db_missing(self, tmp_path: Path) -> None:
        # Create key files
        key_path = tmp_path / "intel_key"
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----\n")  # nosec
        pub_path = tmp_path / "intel_key.pub"
        pub_path.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake test@host\n")

        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'nonexistent' / 'game.db'}\n"
            f"intel_host = intel.example.com\n"
            f"intel_key = {key_path}\n"
        )

        cli = build_cli(config_path=config_path)
        assert cli._intel_context_factory is not None
        push, pull, _, _ = cli._intel_context_factory(None)
        assert push is None
        assert pull is None


class TestIntelWiringErrors:
    def test_missing_private_key_raises(self, tmp_path: Path) -> None:
        pub_path = tmp_path / "intel_key.pub"
        pub_path.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFake test@host\n")

        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            f"intel_host = intel.example.com\n"
            f"intel_key = {tmp_path / 'intel_key'}\n"
        )

        with pytest.raises(IntelKeyError, match="Private key not found"):
            AppContext(config_path=config_path)

    def test_missing_public_key_raises(self, tmp_path: Path) -> None:
        key_path = tmp_path / "intel_key"
        key_path.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n-----END OPENSSH PRIVATE KEY-----\n")  # nosec

        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            f"intel_host = intel.example.com\n"
            f"intel_key = {key_path}\n"
        )

        with pytest.raises(IntelKeyError, match="Public key not found"):
            AppContext(config_path=config_path)

    def test_empty_intel_host_treated_as_disabled(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[DEFAULT]\n"
            "default_profile = default\n\n"
            "[profile:default]\n"
            f"db = {tmp_path / 'game.db'}\n"
            "intel_host = \n"
        )

        ctx = AppContext(config_path=config_path)
        try:
            assert ctx.sync_worker is None
            assert ctx.intel_config is None
        finally:
            ctx.close()
