"""Tests for the CLI sector-art command."""

import pytest

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.compose import AppContext
from tw_guidance_computer.domain.models import Port, Sector


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
