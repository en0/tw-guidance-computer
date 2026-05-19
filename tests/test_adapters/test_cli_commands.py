"""Tests for CLI commands."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.application.use_cases import UseCases
from tw_guidance_computer.compose import AppContext
from tw_guidance_computer.domain.models import PlayerStatus, Port, Profile, ProfileListing, SafeHarborRoute, Sector


@pytest.fixture()
def ctx(tmp_path):
    return AppContext(db_path=tmp_path / "test.db")


@pytest.fixture()
def store(ctx):
    return ctx.store


@pytest.fixture()
def cli(ctx):
    return CliAdapter(ctx.use_cases)


class TestSectorArt:
    def test_unexplored_sector_exits(self, cli, store, capsys):
        with pytest.raises(SystemExit, match="1"):
            cli.sector_art(999)
        assert "has not been explored" in capsys.readouterr().err

    def test_known_but_unexplored_exits(self, cli, store, capsys):
        store.upsert_sector(Sector(id=50, region="Test", explored=False))
        with pytest.raises(SystemExit, match="1"):
            cli.sector_art(50)
        assert "has not been explored" in capsys.readouterr().err

    def test_renders_explored_sector(self, cli, store, capsys):
        store.upsert_sector(Sector(id=865, region="The Federation", explored=True))
        store.upsert_port(Port(sector_id=865, name="Regel Station", port_class=4, port_type="SSB"))

        cli.sector_art(865)

        output = capsys.readouterr().out
        assert "Sector 865" in output
        assert "The Federation" in output
        # Should have some non-whitespace art content
        lines = output.strip().split("\n")
        assert len(lines) > 5

    def test_renders_empty_explored_sector(self, cli, store, capsys):
        store.upsert_sector(Sector(id=42, region="uncharted space", explored=True))

        cli.sector_art(42)

        output = capsys.readouterr().out
        assert "Sector 42" in output


class TestSafeHarbor:
    def test_route_found(self, cli, capsys):
        mock_status = MagicMock()
        mock_status.execute.return_value = PlayerStatus(sector_id=616, turns_remaining=100, credits=500)
        mock_harbor = MagicMock()
        mock_harbor.execute.return_value = SafeHarborRoute(
            destination_sector=1, destination_name="The Federation", route=[616, 214, 1]
        )
        cli._uc = MagicMock(get_player_status=mock_status, find_safe_harbor=mock_harbor)

        cli.safe_harbor()

        out = capsys.readouterr().out
        assert "Safe harbor from sector 616:" in out
        assert "Sector 1 (The Federation)" in out
        assert "616 \u2192 214 \u2192 1 (2 hops)" in out

    def test_already_safe(self, cli, capsys):
        mock_status = MagicMock()
        mock_status.execute.return_value = PlayerStatus(sector_id=1, turns_remaining=100, credits=500)
        mock_harbor = MagicMock()
        mock_harbor.execute.return_value = SafeHarborRoute(
            destination_sector=1, destination_name="The Federation", route=[1]
        )
        cli._uc = MagicMock(get_player_status=mock_status, find_safe_harbor=mock_harbor)

        cli.safe_harbor()

        out = capsys.readouterr().out
        assert "You are currently in a safe sector (The Federation)." in out

    def test_no_route(self, cli, capsys):
        mock_status = MagicMock()
        mock_status.execute.return_value = PlayerStatus(sector_id=616, turns_remaining=100, credits=500)
        mock_harbor = MagicMock()
        mock_harbor.execute.return_value = None
        cli._uc = MagicMock(get_player_status=mock_status, find_safe_harbor=mock_harbor)

        cli.safe_harbor()

        out = capsys.readouterr().out
        assert "No known route to safe space from sector 616." in out
        assert "Explore more sectors" in out

    def test_no_player_status(self, cli, capsys):
        mock_status = MagicMock()
        mock_status.execute.return_value = None
        cli._uc = MagicMock(get_player_status=mock_status)

        with pytest.raises(SystemExit):
            cli.safe_harbor()

        err = capsys.readouterr().err
        assert "No player position known" in err


class TestProfileCreate:
    def test_profile_create_prints_confirmation(self, ctx, capsys):
        mock_create = MagicMock()
        mock_create.execute.return_value = Profile(name="alpha", db_path="/tmp/alpha.db")
        fields = {
            f.name: getattr(ctx.use_cases, f.name)
            for f in ctx.use_cases.__dataclass_fields__.values()
            if f.name not in ("create_profile", "list_profiles")
        }
        use_cases = UseCases(**fields, create_profile=mock_create, list_profiles=None)
        cli = CliAdapter(use_cases)

        cli.profile_create("alpha")

        out = capsys.readouterr().out
        assert "Created profile 'alpha'" in out
        assert "/tmp/alpha.db" in out


class TestProfileList:
    def test_profile_list_marks_default(self, ctx, capsys):
        mock_list = MagicMock()
        mock_list.execute.return_value = ProfileListing(
            profiles=[
                Profile(name="alpha", db_path="/tmp/alpha.db"),
                Profile(name="beta", db_path="/tmp/beta.db"),
            ],
            default_name="alpha",
        )
        use_cases = UseCases(
            **{
                f.name: getattr(ctx.use_cases, f.name)
                for f in ctx.use_cases.__dataclass_fields__.values()
                if f.name not in ("create_profile", "list_profiles")
            },
            create_profile=None,
            list_profiles=mock_list,
        )
        cli = CliAdapter(use_cases)

        cli.profile_list()

        out = capsys.readouterr().out
        lines = out.split("\n")
        assert "  * alpha (default)" in lines[0]
        assert "    beta" in lines[1]
        assert "(default)" not in lines[1]
