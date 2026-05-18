"""Tests for CLI commands."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.application.use_cases import UseCases
from tw_guidance_computer.compose import AppContext
from tw_guidance_computer.domain.models import Port, Profile, ProfileListing, Sector


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
