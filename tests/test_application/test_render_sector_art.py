"""Tests for the RenderSectorArt use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.application.render_sector_art import RenderSectorArt
from tw_guidance_computer.domain.models import Port


@pytest.fixture()
def mock_store():
    return MagicMock(spec=GameStateReader)


@pytest.fixture()
def render_sector_art(mock_store):
    return RenderSectorArt(mock_store)


class TestRenderSectorArt:
    def test_empty_sector(self, render_sector_art, mock_store):
        mock_store.get_port.return_value = None
        mock_store.has_planet.return_value = False

        grid = render_sector_art.execute(999, 80, 14)

        assert len(grid) == 14
        assert all(len(row) == 80 for row in grid)
        mock_store.get_port.assert_called_once_with(999)
        mock_store.has_planet.assert_called_once_with(999)

    def test_port_only(self, render_sector_art, mock_store):
        mock_store.get_port.return_value = Port(
            sector_id=100, name="Regel Station", port_class=4, port_type="SSB"
        )
        mock_store.has_planet.return_value = False

        grid = render_sector_art.execute(100, 80, 14)

        assert len(grid) == 14
        # Port art should add non-space characters beyond starfield
        non_space = sum(1 for row in grid for cell in row if cell.char != " ")
        assert non_space > 20

    def test_port_with_planet(self, render_sector_art, mock_store):
        mock_store.get_port.return_value = Port(
            sector_id=616, name="Trader Vic's", port_class=6, port_type="SBS"
        )
        mock_store.has_planet.return_value = True

        grid = render_sector_art.execute(616, 80, 14)

        assert len(grid) == 14
        assert all(len(row) == 80 for row in grid)

    def test_stardock_detected_from_port_class_zero(self, render_sector_art, mock_store):
        mock_store.get_port.return_value = Port(
            sector_id=1, name="Sol", port_class=0, port_type="Special"
        )
        mock_store.has_planet.return_value = True

        grid = render_sector_art.execute(1, 80, 14)

        # Should render without error — stardock + planet + port
        assert len(grid) == 14

    def test_correct_dimensions(self, render_sector_art, mock_store):
        mock_store.get_port.return_value = None
        mock_store.has_planet.return_value = False

        grid = render_sector_art.execute(50, 100, 20)

        assert len(grid) == 20
        assert all(len(row) == 100 for row in grid)
