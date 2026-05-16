"""Tests for the CLI sector-art command."""

import pytest

from tw_guidance_computer.adapters.cli_commands import CliAdapter
from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.domain.exceptions import SectorNotFoundError
from tw_guidance_computer.domain.models import Port, Sector


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


@pytest.fixture()
def cli(store):
    return CliAdapter(store)


class TestSectorArt:
    def test_unexplored_sector_raises(self, cli, store):
        with pytest.raises(SectorNotFoundError, match="has not been explored"):
            cli.sector_art(999)

    def test_known_but_unexplored_raises(self, cli, store):
        store.upsert_sector(Sector(id=50, region="Test", explored=False))
        with pytest.raises(SectorNotFoundError, match="has not been explored"):
            cli.sector_art(50)

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
