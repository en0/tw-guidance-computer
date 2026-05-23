"""Tests for CLI intel push/pull commands."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.domain.exceptions import IntelConnectError, IntelTransferError
from tw_guidance_computer.domain.models import IntelConfig, IntelMergeResult


@pytest.fixture()
def mock_push_intel():
    return MagicMock()


@pytest.fixture()
def mock_pull_intel():
    return MagicMock()


@pytest.fixture()
def intel_config():
    return IntelConfig(host="intel.example.com", key_path="/tmp/key", port=2222)


@pytest.fixture()
def mock_intel_store():
    store = MagicMock()
    store.get_local_sectors.return_value = [(MagicMock(), 1.0)] * 142
    store.get_local_ports.return_value = [(MagicMock(), 1.0)] * 67
    store.get_local_warps.return_value = [(MagicMock(), 1.0)] * 312
    store.get_local_planets.return_value = [(MagicMock(), 1.0)] * 4
    return store


@pytest.fixture()
def cli_with_intel(mock_push_intel, mock_pull_intel, intel_config, mock_intel_store):
    return CliAdapter(
        create_profile=MagicMock(),
        list_profiles=MagicMock(),
        game_context_factory=MagicMock(),
        push_intel=mock_push_intel,
        pull_intel=mock_pull_intel,
        intel_config=intel_config,
        intel_store=mock_intel_store,
    )


@pytest.fixture()
def cli_no_intel():
    return CliAdapter(
        create_profile=MagicMock(),
        list_profiles=MagicMock(),
        game_context_factory=MagicMock(),
    )


class TestIntelPush:
    def test_success_output(self, cli_with_intel, mock_push_intel, capsys):
        mock_push_intel.execute.return_value = 525

        cli_with_intel.run(["intel", "push"])

        out = capsys.readouterr().out
        assert "Exporting 142 sectors, 67 ports, 312 warps, 4 planets..." in out
        assert "Uploading to intel.example.com:2222..." in out
        assert "Done. Pushed 525 records." in out

    def test_not_configured_exits(self, cli_no_intel, capsys):
        with pytest.raises(SystemExit, match="1"):
            cli_no_intel.run(["intel", "push"])

        err = capsys.readouterr().err
        assert "Intel not configured" in err
        assert "intel_host" in err

    def test_connect_error_exits(self, cli_with_intel, mock_push_intel, capsys):
        mock_push_intel.execute.side_effect = IntelConnectError("Connection timed out")

        with pytest.raises(SystemExit, match="1"):
            cli_with_intel.run(["intel", "push"])

        err = capsys.readouterr().err
        assert "Connection timed out" in err

    def test_transfer_error_exits(self, cli_with_intel, mock_push_intel, capsys):
        mock_push_intel.execute.side_effect = IntelTransferError("Upload failed")

        with pytest.raises(SystemExit, match="1"):
            cli_with_intel.run(["intel", "push"])

        err = capsys.readouterr().err
        assert "Upload failed" in err


class TestIntelPull:
    def test_success_output(self, cli_with_intel, mock_pull_intel, capsys):
        mock_pull_intel.execute.return_value = IntelMergeResult(
            sectors_added=45, ports_added=23, ports_updated=12, warps_added=89, planets_added=3
        )

        cli_with_intel.run(["intel", "pull"])

        out = capsys.readouterr().out
        assert "+45 sectors" in out
        assert "+23 ports" in out
        assert "12 ports updated (fresher)" in out
        assert "+89 warps" in out
        assert "+3 planets" in out
        assert "Done." in out

    def test_not_configured_exits(self, cli_no_intel, capsys):
        with pytest.raises(SystemExit, match="1"):
            cli_no_intel.run(["intel", "pull"])

        err = capsys.readouterr().err
        assert "Intel not configured" in err
        assert "intel_host" in err

    def test_connect_error_exits(self, cli_with_intel, mock_pull_intel, capsys):
        mock_pull_intel.execute.side_effect = IntelConnectError("Connection refused")

        with pytest.raises(SystemExit, match="1"):
            cli_with_intel.run(["intel", "pull"])

        err = capsys.readouterr().err
        assert "Connection refused" in err

    def test_zero_results(self, cli_with_intel, mock_pull_intel, capsys):
        mock_pull_intel.execute.return_value = IntelMergeResult()

        cli_with_intel.run(["intel", "pull"])

        out = capsys.readouterr().out
        assert "+0 sectors" in out
        assert "Done." in out

    def test_pull_called_without_budget(self, cli_with_intel, mock_pull_intel, capsys):
        mock_pull_intel.execute.return_value = IntelMergeResult()

        cli_with_intel.run(["intel", "pull"])

        mock_pull_intel.execute.assert_called_once_with()


class TestIntelProfileRouting:
    def test_factory_called_with_profile_on_push(self, capsys):
        mock_push = MagicMock()
        mock_push.execute.return_value = 10
        mock_store = MagicMock()
        mock_store.get_local_sectors.return_value = []
        mock_store.get_local_ports.return_value = []
        mock_store.get_local_warps.return_value = []
        mock_store.get_local_planets.return_value = []
        config = IntelConfig(host="h", key_path="/k", port=22)

        factory = MagicMock(return_value=(mock_push, MagicMock(), config, mock_store))

        cli = CliAdapter(
            create_profile=MagicMock(),
            list_profiles=MagicMock(),
            game_context_factory=MagicMock(),
            intel_context_factory=factory,
        )
        cli.run(["-p", "debug", "intel", "push"])

        factory.assert_called_once_with("debug")

    def test_factory_called_with_profile_on_pull(self, capsys):
        mock_pull = MagicMock()
        mock_pull.execute.return_value = IntelMergeResult()

        factory = MagicMock(return_value=(MagicMock(), mock_pull, MagicMock(), MagicMock()))

        cli = CliAdapter(
            create_profile=MagicMock(),
            list_profiles=MagicMock(),
            game_context_factory=MagicMock(),
            intel_context_factory=factory,
        )
        cli.run(["-p", "myprofile", "intel", "pull"])

        factory.assert_called_once_with("myprofile")

    def test_factory_called_with_none_when_no_profile(self, capsys):
        mock_pull = MagicMock()
        mock_pull.execute.return_value = IntelMergeResult()

        factory = MagicMock(return_value=(MagicMock(), mock_pull, MagicMock(), MagicMock()))

        cli = CliAdapter(
            create_profile=MagicMock(),
            list_profiles=MagicMock(),
            game_context_factory=MagicMock(),
            intel_context_factory=factory,
        )
        cli.run(["intel", "pull"])

        factory.assert_called_once_with(None)
