"""Tests for domain sector art generation."""

from tw_guidance_computer.domain.sector_art import (
    compose_scene,
    generate_planet_art,
    generate_port_art,
    generate_stardock_art,
    generate_starfield,
)


class TestGeneratePortArt:
    def test_deterministic(self):
        grid1 = generate_port_art("Regel Station", 25, 12)
        grid2 = generate_port_art("Regel Station", 25, 12)
        assert grid1 == grid2

    def test_different_names_differ(self):
        grid1 = generate_port_art("Regel Station", 25, 12)
        grid2 = generate_port_art("Trader Vic's", 25, 12)
        assert grid1 != grid2

    def test_correct_dimensions(self):
        grid = generate_port_art("Test Port", 20, 10)
        assert len(grid) == 10
        assert all(len(row) == 20 for row in grid)

    def test_returns_char_color_tuples(self):
        grid = generate_port_art("Test Port", 15, 8)
        for row in grid:
            for cell in row:
                assert isinstance(cell, tuple)
                assert len(cell) == 2


class TestGenerateStarfield:
    def test_deterministic(self):
        grid1 = generate_starfield(80, 14, seed=42)
        grid2 = generate_starfield(80, 14, seed=42)
        assert grid1 == grid2

    def test_different_seeds_differ(self):
        grid1 = generate_starfield(80, 14, seed=42)
        grid2 = generate_starfield(80, 14, seed=99)
        assert grid1 != grid2

    def test_correct_dimensions(self):
        grid = generate_starfield(60, 10, seed=1)
        assert len(grid) == 10
        assert all(len(row) == 60 for row in grid)

    def test_sparse(self):
        grid = generate_starfield(80, 14, seed=42)
        non_empty = sum(1 for row in grid for ch, _ in row if ch != " ")
        total = 80 * 14
        assert non_empty < total * 0.1


class TestGeneratePlanetArt:
    def test_deterministic(self):
        grid1 = generate_planet_art(80, 14)
        grid2 = generate_planet_art(80, 14)
        assert grid1 == grid2

    def test_correct_dimensions(self):
        grid = generate_planet_art(60, 10)
        assert len(grid) == 10
        assert all(len(row) == 60 for row in grid)

    def test_bottom_left_anchor(self):
        grid = generate_planet_art(80, 14)
        # Bottom-left should have planet pixels
        has_bottom_left = any(grid[y][x] is not None for y in range(10, 14) for x in range(10))
        assert has_bottom_left
        # Top-right should be empty
        has_top_right = any(grid[y][x] is not None for y in range(3) for x in range(60, 80))
        assert not has_top_right


class TestGenerateStardockArt:
    def test_deterministic(self):
        grid1 = generate_stardock_art(80, 14)
        grid2 = generate_stardock_art(80, 14)
        assert grid1 == grid2

    def test_correct_dimensions(self):
        grid = generate_stardock_art(80, 14)
        assert len(grid) == 14
        assert all(len(row) == 80 for row in grid)

    def test_right_of_center(self):
        grid = generate_stardock_art(80, 14)
        # Stardock should be in the right portion
        has_right = any(grid[y][x] is not None for y in range(14) for x in range(60, 80))
        assert has_right


class TestComposeScene:
    def test_empty_sector_is_starfield_only(self):
        grid = compose_scene(80, 14, port_name=None, has_planet=False, has_stardock=False, seed=42)
        assert len(grid) == 14
        assert all(len(row) == 80 for row in grid)

    def test_port_only(self):
        grid = compose_scene(80, 14, port_name="Test Port", has_planet=False, has_stardock=False, seed=42)
        # Should have non-space characters from port art
        non_space = sum(1 for row in grid for cell in row if cell.char != " ")
        empty_grid = compose_scene(80, 14, port_name=None, has_planet=False, has_stardock=False, seed=42)
        empty_non_space = sum(1 for row in empty_grid for cell in row if cell.char != " ")
        assert non_space > empty_non_space

    def test_full_scene(self):
        grid = compose_scene(80, 14, port_name="Regel Station", has_planet=True, has_stardock=True, seed=42)
        assert len(grid) == 14
        assert all(len(row) == 80 for row in grid)

    def test_deterministic_with_same_seed(self):
        grid1 = compose_scene(80, 14, port_name="Test", has_planet=True, has_stardock=True, seed=42)
        grid2 = compose_scene(80, 14, port_name="Test", has_planet=True, has_stardock=True, seed=42)
        assert grid1 == grid2
