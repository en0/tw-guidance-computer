"""Tests for CLI commands."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.compose import AppContext
from tw_guidance_computer.domain.exceptions import DatabaseNotFoundError, GuidanceError
from tw_guidance_computer.domain.models import PlayerStatus, Port, ProfileListing, SafeHarborRoute, Sector


@pytest.fixture()
def mock_use_cases():
    return MagicMock()


@pytest.fixture()
def mock_close():
    return MagicMock()


@pytest.fixture()
def mock_game_context_factory(mock_use_cases, mock_close):
    return MagicMock(return_value=(mock_use_cases, mock_close))


@pytest.fixture()
def mock_create_profile():
    return MagicMock()


@pytest.fixture()
def mock_list_profiles():
    return MagicMock()


@pytest.fixture()
def cli(mock_create_profile, mock_list_profiles, mock_game_context_factory):
    return CliAdapter(
        create_profile=mock_create_profile,
        list_profiles=mock_list_profiles,
        game_context_factory=mock_game_context_factory,
    )


@pytest.fixture()
def ctx(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[DEFAULT]\n"
        "default_profile = default\n\n"
        "[profile:default]\n"
        f"db = {tmp_path / 'test.db'}\n"
    )
    return AppContext(config_path=config_path)


@pytest.fixture()
def integration_cli(ctx):
    """CLI adapter wired to a real store for integration-style tests."""
    mock_close = MagicMock()
    mock_create = MagicMock()
    mock_list = MagicMock()
    factory = MagicMock(return_value=(ctx.use_cases, mock_close))
    return CliAdapter(
        create_profile=mock_create,
        list_profiles=mock_list,
        game_context_factory=factory,
    )


@pytest.fixture()
def store(ctx):
    return ctx.store


class TestDispatchProfile:
    def test_profile_create(self, cli, mock_create_profile, capsys):
        mock_create_profile.execute.return_value = MagicMock(name="test", db_path="/tmp/test.db")
        cli.run(["profile", "create", "test"])
        mock_create_profile.execute.assert_called_once_with("test")

    def test_profile_list(self, cli, mock_list_profiles, capsys):
        mock_list_profiles.execute.return_value = ProfileListing(
            profiles=[], default_name="default"
        )
        cli.run(["profile", "list"])
        mock_list_profiles.execute.assert_called_once()

    def test_profile_does_not_call_game_factory(self, cli, mock_game_context_factory, mock_list_profiles):
        mock_list_profiles.execute.return_value = ProfileListing(
            profiles=[], default_name="default"
        )
        cli.run(["profile", "list"])
        mock_game_context_factory.assert_not_called()


class TestDispatchGame:
    def test_status_calls_factory_and_close(self, cli, mock_game_context_factory, mock_use_cases, mock_close, capsys):
        mock_use_cases.get_database_summary.execute.return_value = MagicMock(
            sectors_total=10, sectors_explored=5, ports_total=3, warps_total=20, port_type_counts={}
        )
        mock_use_cases.get_player_status.execute.return_value = None
        cli.run(["status"])
        mock_game_context_factory.assert_called_once_with(None)
        mock_close.assert_called_once()

    def test_profile_flag_passed_to_factory(self, cli, mock_game_context_factory, mock_use_cases, mock_close, capsys):
        mock_use_cases.get_database_summary.execute.return_value = MagicMock(
            sectors_total=0, sectors_explored=0, ports_total=0, warps_total=0, port_type_counts={}
        )
        mock_use_cases.get_player_status.execute.return_value = None
        cli.run(["--profile", "myprofile", "status"])
        mock_game_context_factory.assert_called_once_with("myprofile")

    def test_close_called_on_handler_error(self, cli, mock_use_cases, mock_close):
        mock_use_cases.get_database_summary.execute.side_effect = GuidanceError("boom")
        with pytest.raises(SystemExit):
            cli.run(["status"])
        mock_close.assert_called_once()

    def test_factory_error_exits(self, cli, mock_game_context_factory, capsys):
        mock_game_context_factory.side_effect = DatabaseNotFoundError("no db")
        with pytest.raises(SystemExit, match="1"):
            cli.run(["status"])
        assert "no db" in capsys.readouterr().err

    def test_no_command_prints_help(self, cli, capsys):
        with pytest.raises(SystemExit, match="0"):
            cli.run([])


class TestSectorArt:
    def test_unexplored_sector_exits(self, integration_cli, store, capsys):
        with pytest.raises(SystemExit, match="1"):
            integration_cli.run(["sector-art", "999"])
        assert "has not been explored" in capsys.readouterr().err

    def test_renders_explored_sector(self, integration_cli, store, capsys):
        store.upsert_sector(Sector(id=865, region="The Federation", explored=True))
        store.upsert_port(Port(sector_id=865, name="Regel Station", port_class=4, port_type="SSB"))

        integration_cli.run(["sector-art", "865"])

        output = capsys.readouterr().out
        assert "Sector 865" in output
        assert "The Federation" in output
        lines = output.strip().split("\n")
        assert len(lines) > 5

    def test_renders_empty_explored_sector(self, integration_cli, store, capsys):
        store.upsert_sector(Sector(id=42, region="uncharted space", explored=True))

        integration_cli.run(["sector-art", "42"])

        output = capsys.readouterr().out
        assert "Sector 42" in output


class TestSafeHarbor:
    def test_route_found(self, cli, mock_use_cases, capsys):
        mock_use_cases.get_player_status.execute.return_value = PlayerStatus(
            sector_id=616, turns_remaining=100, credits=500
        )
        mock_use_cases.find_safe_harbor.execute.return_value = SafeHarborRoute(
            destination_sector=1, destination_name="The Federation", route=[616, 214, 1]
        )

        cli.run(["safe-harbor"])

        out = capsys.readouterr().out
        assert "Safe harbor from sector 616:" in out
        assert "Sector 1 (The Federation)" in out
        assert "616 \u2192 214 \u2192 1 (2 hops)" in out

    def test_already_safe(self, cli, mock_use_cases, capsys):
        mock_use_cases.get_player_status.execute.return_value = PlayerStatus(
            sector_id=1, turns_remaining=100, credits=500
        )
        mock_use_cases.find_safe_harbor.execute.return_value = SafeHarborRoute(
            destination_sector=1, destination_name="The Federation", route=[1]
        )

        cli.run(["safe-harbor"])

        out = capsys.readouterr().out
        assert "You are currently in a safe sector (The Federation)." in out

    def test_no_route(self, cli, mock_use_cases, capsys):
        mock_use_cases.get_player_status.execute.return_value = PlayerStatus(
            sector_id=616, turns_remaining=100, credits=500
        )
        mock_use_cases.find_safe_harbor.execute.return_value = None

        cli.run(["safe-harbor"])

        out = capsys.readouterr().out
        assert "No known route to safe space from sector 616." in out
        assert "Explore more sectors" in out

    def test_no_player_status(self, cli, mock_use_cases, capsys):
        mock_use_cases.get_player_status.execute.return_value = None

        with pytest.raises(SystemExit):
            cli.run(["safe-harbor"])

        err = capsys.readouterr().err
        assert "No player position known" in err
