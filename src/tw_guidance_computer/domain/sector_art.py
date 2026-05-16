"""Domain: deterministic ASCII art generation for sector scenes.

Pure functions — no I/O. Uses only stdlib (hashlib, random, dataclasses, enum).
All functions are deterministic given the same inputs.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from enum import Enum

# --- Tile System ---


class TileCategory(Enum):
    """Categories of tiles for WFC generation."""

    HULL = "hull"
    FRAME = "frame"
    PIPE = "pipe"
    ANTENNA = "antenna"
    WINDOW = "window"
    DOCK = "dock"
    EMPTY = "empty"


@dataclass(frozen=True)
class Tile:
    """A single tile with adjacency constraints."""

    char: str
    category: TileCategory
    north: frozenset[TileCategory]
    south: frozenset[TileCategory]
    east: frozenset[TileCategory]
    west: frozenset[TileCategory]
    weight: float = 1.0


ALL = frozenset(TileCategory)
SOLID = frozenset(
    {TileCategory.HULL, TileCategory.FRAME, TileCategory.PIPE, TileCategory.WINDOW, TileCategory.DOCK}
)
STRUCTURAL = frozenset(
    {TileCategory.HULL, TileCategory.FRAME, TileCategory.PIPE, TileCategory.ANTENNA, TileCategory.WINDOW}
)
EDGE = frozenset({TileCategory.EMPTY, TileCategory.FRAME, TileCategory.DOCK, TileCategory.ANTENNA})

TILES: list[Tile] = [
    # Hull plating
    Tile("█", TileCategory.HULL, STRUCTURAL, STRUCTURAL, STRUCTURAL, STRUCTURAL, 3.0),
    Tile("▓", TileCategory.HULL, STRUCTURAL, STRUCTURAL, STRUCTURAL, STRUCTURAL, 2.5),
    Tile("░", TileCategory.HULL, ALL, ALL, ALL, ALL, 2.0),
    # Structural frame
    Tile("╔", TileCategory.FRAME, EDGE, SOLID, SOLID, EDGE, 0.8),
    Tile("╗", TileCategory.FRAME, EDGE, SOLID, EDGE, SOLID, 0.8),
    Tile("╚", TileCategory.FRAME, SOLID, EDGE, SOLID, EDGE, 0.8),
    Tile("╝", TileCategory.FRAME, SOLID, EDGE, EDGE, SOLID, 0.8),
    Tile("═", TileCategory.FRAME, ALL, ALL, SOLID | {TileCategory.FRAME}, SOLID | {TileCategory.FRAME}, 1.5),
    Tile("║", TileCategory.FRAME, SOLID | {TileCategory.FRAME}, SOLID | {TileCategory.FRAME}, ALL, ALL, 1.5),
    # Pipes
    Tile(
        "─",
        TileCategory.PIPE,
        ALL,
        ALL,
        frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}),
        frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}),
        0.5,
    ),
    Tile(
        "│",
        TileCategory.PIPE,
        frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.ANTENNA}),
        frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}),
        ALL,
        ALL,
        0.5,
    ),
    Tile("┌", TileCategory.PIPE, EDGE | {TileCategory.HULL}, SOLID, SOLID, EDGE | {TileCategory.HULL}, 0.3),
    Tile("┐", TileCategory.PIPE, EDGE | {TileCategory.HULL}, SOLID, EDGE | {TileCategory.HULL}, SOLID, 0.3),
    Tile("└", TileCategory.PIPE, SOLID, EDGE | {TileCategory.HULL}, SOLID, EDGE | {TileCategory.HULL}, 0.3),
    Tile("┘", TileCategory.PIPE, SOLID, EDGE | {TileCategory.HULL}, EDGE | {TileCategory.HULL}, SOLID, 0.3),
    Tile("┬", TileCategory.PIPE, EDGE, SOLID, SOLID, SOLID, 0.2),
    Tile("┴", TileCategory.PIPE, SOLID, EDGE, SOLID, SOLID, 0.2),
    Tile("├", TileCategory.PIPE, SOLID, SOLID, SOLID, EDGE, 0.2),
    Tile("┤", TileCategory.PIPE, SOLID, SOLID, EDGE, SOLID, 0.2),
    # Antenna
    Tile("╥", TileCategory.ANTENNA, EDGE, SOLID, ALL, ALL, 0.1),
    Tile("╨", TileCategory.ANTENNA, SOLID, EDGE, ALL, ALL, 0.1),
    Tile(
        "↑",
        TileCategory.ANTENNA,
        EDGE,
        frozenset({TileCategory.ANTENNA, TileCategory.FRAME, TileCategory.HULL}),
        EDGE,
        EDGE,
        0.08,
    ),
    Tile("¤", TileCategory.ANTENNA, EDGE, frozenset({TileCategory.ANTENNA, TileCategory.FRAME}), EDGE, EDGE, 0.08),
    # Windows
    Tile("▪", TileCategory.WINDOW, SOLID, SOLID, SOLID, SOLID, 0.4),
    Tile("▫", TileCategory.WINDOW, SOLID, SOLID, SOLID, SOLID, 0.4),
    Tile("[", TileCategory.WINDOW, ALL, ALL, frozenset({TileCategory.WINDOW, TileCategory.HULL}), ALL, 0.2),
    Tile("]", TileCategory.WINDOW, ALL, ALL, ALL, frozenset({TileCategory.WINDOW, TileCategory.HULL}), 0.2),
    # Docking
    Tile(">", TileCategory.DOCK, ALL, ALL, EDGE, SOLID, 0.08),
    Tile("<", TileCategory.DOCK, ALL, ALL, SOLID, EDGE, 0.08),
    Tile("⊏", TileCategory.DOCK, SOLID, SOLID, SOLID, EDGE, 0.06),
    Tile("⊐", TileCategory.DOCK, SOLID, SOLID, EDGE, SOLID, 0.06),
    # Empty
    Tile(" ", TileCategory.EMPTY, ALL, ALL, ALL, ALL, 0.1),
]


# --- Color System ---


@dataclass(frozen=True)
class ColorScheme:
    """Color palette for a station: base shades + category accents."""

    base_shades: tuple[int, ...]
    pipe_accents: tuple[int, ...]
    window_accents: tuple[int, ...]
    antenna_accents: tuple[int, ...]
    dock_accents: tuple[int, ...]


_BASE_HUES: list[dict[str, tuple[int, ...]]] = [
    {
        "base": (240, 243, 245, 248, 250), "pipe": (178, 220, 136),
        "window": (39, 45, 51), "antenna": (196, 203), "dock": (255, 252),
    },
    {
        "base": (17, 18, 19, 20, 24), "pipe": (166, 172, 208),
        "window": (45, 51, 87), "antenna": (255, 231), "dock": (39, 45),
    },
    {
        "base": (236, 238, 240, 243, 245), "pipe": (130, 166, 172),
        "window": (28, 34, 40), "antenna": (39, 75), "dock": (178, 220),
    },
    {
        "base": (22, 23, 28, 29, 34), "pipe": (250, 252, 255),
        "window": (220, 226, 228), "antenna": (196, 160), "dock": (45, 51),
    },
    {
        "base": (53, 54, 55, 56, 57), "pipe": (37, 43, 44),
        "window": (163, 169, 201), "antenna": (220, 178), "dock": (255, 252),
    },
    {
        "base": (94, 95, 130, 131, 137), "pipe": (178, 214, 220),
        "window": (39, 45, 75), "antenna": (255, 231), "dock": (166, 172),
    },
    {
        "base": (23, 29, 30, 36, 37), "pipe": (250, 252, 255),
        "window": (166, 172, 208), "antenna": (201, 163), "dock": (220, 226),
    },
    {
        "base": (233, 235, 237, 239, 241), "pipe": (33, 39, 69),
        "window": (124, 160, 196), "antenna": (34, 40), "dock": (245, 250),
    },
]


def _rotate_tuple(t: tuple[int, ...], n: int) -> tuple[int, ...]:
    if not t:
        return t
    n = n % len(t)
    return t[n:] + t[:n]


def _make_color_scheme(seed: int) -> ColorScheme:
    """Build a color scheme from the seed."""
    idx = seed % len(_BASE_HUES)
    hue = _BASE_HUES[idx]
    rotation = (seed >> 8) % 3
    return ColorScheme(
        base_shades=hue["base"],
        pipe_accents=_rotate_tuple(hue["pipe"], rotation),
        window_accents=_rotate_tuple(hue["window"], rotation),
        antenna_accents=_rotate_tuple(hue["antenna"], rotation),
        dock_accents=_rotate_tuple(hue["dock"], rotation),
    )


def _color_for_tile(tile: Tile, x: int, y: int, scheme: ColorScheme, rng: random.Random) -> str:
    """Pick ANSI 256-color code for a tile."""
    if tile.char == " ":
        return ""
    c = "\033[38;5;{}m"
    if tile.category == TileCategory.HULL:
        idx = (x * 3 + y * 7 + rng.randint(0, 1)) % len(scheme.base_shades)
        return c.format(scheme.base_shades[idx])
    if tile.category == TileCategory.FRAME:
        if rng.random() < 0.3:
            return c.format(scheme.base_shades[-1])
        idx = (x + y * 5) % len(scheme.base_shades)
        return c.format(scheme.base_shades[idx])
    if tile.category == TileCategory.PIPE:
        idx = (x * 2 + y) % len(scheme.pipe_accents)
        return c.format(scheme.pipe_accents[idx])
    if tile.category == TileCategory.WINDOW:
        idx = (x + y * 3) % len(scheme.window_accents)
        return c.format(scheme.window_accents[idx])
    if tile.category == TileCategory.ANTENNA:
        idx = (x + y) % len(scheme.antenna_accents)
        return c.format(scheme.antenna_accents[idx])
    if tile.category == TileCategory.DOCK:
        idx = (x + y) % len(scheme.dock_accents)
        return c.format(scheme.dock_accents[idx])
    return c.format(scheme.base_shades[0])


# --- Silhouette Masks ---


class Silhouette(Enum):
    """Station silhouette shapes."""

    TOWER = "tower"
    DOME = "dome"
    SPIRE = "spire"
    WIDE = "wide"
    CROSS = "cross"
    DIAMOND = "diamond"


def _make_silhouette(shape: Silhouette, width: int, height: int) -> list[list[bool]]:
    """Generate a boolean mask for tile placement."""
    mask = [[False] * width for _ in range(height)]
    cx = width // 2
    cy = height // 2

    if shape == Silhouette.TOWER:
        for y in range(height):
            taper = max(0, (height - y - 1) * width // (height * 4))
            left = cx - width // 4 + taper
            right = cx + width // 4 - taper
            for x in range(max(0, left), min(width, right + 1)):
                mask[y][x] = True
    elif shape == Silhouette.DOME:
        base_top = height // 2
        radius = width // 3
        for y in range(height):
            if y >= base_top:
                left = cx - width // 3
                right = cx + width // 3
            else:
                dy = base_top - y
                if dy > radius:
                    continue
                half_w = int((radius**2 - dy**2) ** 0.5)
                left = cx - half_w
                right = cx + half_w
            for x in range(max(0, left), min(width, right + 1)):
                mask[y][x] = True
    elif shape == Silhouette.SPIRE:
        for y in range(height):
            progress = y / max(height - 1, 1)
            half_w = int(progress * width // 2.5)
            for x in range(cx - half_w, cx + half_w + 1):
                if 0 <= x < width:
                    mask[y][x] = True
    elif shape == Silhouette.WIDE:
        for y in range(height // 4, height * 3 // 4):
            for x in range(width // 6, width * 5 // 6):
                mask[y][x] = True
    elif shape == Silhouette.CROSS:
        arm_w = width // 5
        arm_h = height // 5
        for y in range(height):
            for x in range(width):
                if abs(x - cx) <= arm_w or abs(y - cy) <= arm_h:
                    mask[y][x] = True
    elif shape == Silhouette.DIAMOND:
        for y in range(height):
            dy = abs(y - cy)
            half_w = int((1 - dy / max(cy, 1)) * width // 2.5)
            if half_w < 0:
                continue
            for x in range(cx - half_w, cx + half_w + 1):
                if 0 <= x < width:
                    mask[y][x] = True

    return mask


# --- Edge Detection ---

_EDGE_CHARS: dict[frozenset[str], str] = {
    frozenset({"N"}): "─",
    frozenset({"S"}): "─",
    frozenset({"E"}): "│",
    frozenset({"W"}): "│",
    frozenset({"N", "E"}): "╗",
    frozenset({"N", "W"}): "╔",
    frozenset({"S", "E"}): "╝",
    frozenset({"S", "W"}): "╚",
    frozenset({"N", "S"}): "║",
    frozenset({"E", "W"}): "═",
    frozenset({"N", "E", "W"}): "╦",
    frozenset({"S", "E", "W"}): "╩",
    frozenset({"N", "S", "E"}): "╣",
    frozenset({"N", "S", "W"}): "╠",
    frozenset({"N", "S", "E", "W"}): "◊",
}


def _detect_edges(mask: list[list[bool]], width: int, height: int) -> list[list[frozenset[str] | None]]:
    """Determine which sides of each cell are exposed to empty space."""
    edges: list[list[frozenset[str] | None]] = [[None] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if not mask[y][x]:
                continue
            exposed: set[str] = set()
            if y == 0 or not mask[y - 1][x]:
                exposed.add("N")
            if y == height - 1 or not mask[y + 1][x]:
                exposed.add("S")
            if x == 0 or not mask[y][x - 1]:
                exposed.add("W")
            if x == width - 1 or not mask[y][x + 1]:
                exposed.add("E")
            if exposed:
                edges[y][x] = frozenset(exposed)
    return edges


def _get_edge_char(exposed: frozenset[str], x: int, y: int, mask: list[list[bool]], width: int, height: int) -> str:
    """Pick edge character considering diagonal slopes."""
    if len(exposed) == 1:
        direction = next(iter(exposed))
        if direction in ("N", "S"):
            check_y = y - 1 if direction == "N" else y + 1
            if 0 <= check_y < height:
                left_out = x > 0 and not mask[check_y][x - 1] and mask[y][x - 1]
                right_out = x < width - 1 and not mask[check_y][x + 1] and mask[y][x + 1]
                if left_out and not right_out:
                    return "/" if direction == "N" else "\\"
                if right_out and not left_out:
                    return "\\" if direction == "N" else "/"
    return _EDGE_CHARS.get(exposed, "█")


# --- WFC Generator ---


@dataclass(frozen=True)
class _GeneratorConfig:
    """Internal config for station generation."""

    width: int
    height: int
    decay: float
    density: float
    symmetry: bool
    silhouette: Silhouette


def generate_port_art(name: str, width: int, height: int) -> list[list[tuple[str, str]]]:
    """Generate deterministic port art from a port name.

    Args:
        name: Port name (used as hash seed).
        width: Art width in characters.
        height: Art height in rows.

    Returns:
        Grid of (character, ansi_color_escape) tuples.
    """
    h = hashlib.sha256(name.encode()).hexdigest()
    seed = int(h[:16], 16)
    rng = random.Random(seed)
    scheme = _make_color_scheme(seed)

    silhouettes = list(Silhouette)
    config = _GeneratorConfig(
        width=width,
        height=height,
        decay=0.4,
        density=0.3 + ((seed >> 16) % 100) / 100.0 * 0.7,
        symmetry=(seed % 10) < 7,
        silhouette=silhouettes[seed % len(silhouettes)],
    )

    mask = _make_silhouette(config.silhouette, width, height)
    gen_width = (width + 1) // 2 if config.symmetry else width

    # WFC collapse
    grid: list[list[Tile | None]] = [[None] * gen_width for _ in range(height)]
    h_runs: list[list[dict[TileCategory, int]]] = [[{} for _ in range(gen_width)] for _ in range(height)]
    v_runs: list[list[dict[TileCategory, int]]] = [[{} for _ in range(gen_width)] for _ in range(height)]

    empty_tile = Tile(" ", TileCategory.EMPTY, ALL, ALL, ALL, ALL)

    for y in range(height):
        for x in range(gen_width):
            mask_x = x
            in_mask = mask[y][mask_x] if mask_x < width else False
            if config.symmetry:
                mirror_x = width - 1 - x
                in_mask = in_mask or (mirror_x < width and mask[y][mirror_x])

            if not in_mask:
                grid[y][x] = empty_tile
                continue

            valid_categories: set[TileCategory] = set(TileCategory)
            if y > 0 and grid[y - 1][x] is not None:
                north_tile = grid[y - 1][x]
                assert north_tile is not None
                valid_categories &= north_tile.south
            if x > 0 and grid[y][x - 1] is not None:
                west_tile = grid[y][x - 1]
                assert west_tile is not None
                valid_categories &= west_tile.east
            if not valid_categories:
                valid_categories = {TileCategory.HULL, TileCategory.EMPTY}

            candidates = [t for t in TILES if t.category in valid_categories]
            if not candidates:
                candidates = [t for t in TILES if t.category == TileCategory.HULL]

            neighbor_cats: list[TileCategory] = []
            if y > 0 and grid[y - 1][x] is not None:
                north_tile = grid[y - 1][x]
                assert north_tile is not None
                neighbor_cats.append(north_tile.category)
            if x > 0 and grid[y][x - 1] is not None:
                west_tile = grid[y][x - 1]
                assert west_tile is not None
                neighbor_cats.append(west_tile.category)

            weights = []
            for tile in candidates:
                w = tile.weight
                matching = sum(1 for nc in neighbor_cats if nc == tile.category)
                if matching > 0:
                    w *= 3.0 * matching
                if x > 0:
                    h_run = h_runs[y][x - 1].get(tile.category, 0)
                    if h_run > 2:
                        w *= (1 - config.decay) ** (h_run - 2)
                if y > 0:
                    v_run = v_runs[y - 1][x].get(tile.category, 0)
                    if v_run > 2:
                        w *= (1 - config.decay) ** (v_run - 2)
                if tile.category == TileCategory.EMPTY:
                    w *= (1 - config.density) * 0.5
                else:
                    w *= config.density
                weights.append(max(w, 0.01))

            chosen = rng.choices(candidates, weights=weights, k=1)[0]
            grid[y][x] = chosen

            if x > 0:
                prev = h_runs[y][x - 1].get(chosen.category, 0)
                h_runs[y][x][chosen.category] = prev + 1
            else:
                h_runs[y][x][chosen.category] = 1
            if y > 0:
                prev = v_runs[y - 1][x].get(chosen.category, 0)
                v_runs[y][x][chosen.category] = prev + 1
            else:
                v_runs[y][x][chosen.category] = 1

    # Edge detection
    edge_map = _detect_edges(mask, width, height)
    edge_color = f"\033[38;5;{scheme.base_shades[-1]}m"

    # Expand to full width
    color_rng = random.Random(seed + 1)
    full_grid: list[list[tuple[str, str]]] = []
    mirror_map = {
        "╔": "╗", "╗": "╔", "╚": "╝", "╝": "╚",
        "┌": "┐", "┐": "┌", "└": "┘", "┘": "└",
        "├": "┤", "┤": "├", ">": "<", "<": ">",
        "⊏": "⊐", "⊐": "⊏", "[": "]", "]": "[",
    }

    for y in range(height):
        row: list[tuple[str, str]] = []
        for x in range(width):
            exposed = edge_map[y][x]
            if exposed:
                char = _get_edge_char(exposed, x, y, mask, width, height)
                row.append((char, edge_color))
                continue

            src_x = x if x < gen_width else width - 1 - x if config.symmetry else x
            src_tile: Tile | None = grid[y][src_x] if src_x < gen_width else None

            if src_tile is None:
                row.append((" ", ""))
            else:
                color = _color_for_tile(src_tile, x, y, scheme, color_rng)
                char = src_tile.char
                if config.symmetry and x >= gen_width:
                    char = mirror_map.get(char, char)
                row.append((char, color))
        full_grid.append(row)

    return full_grid


# --- Static Art ---


def generate_starfield(width: int, height: int, seed: int) -> list[list[tuple[str, str]]]:
    """Generate a sparse starfield background.

    Args:
        width: Grid width.
        height: Grid height.
        seed: RNG seed for star placement.

    Returns:
        Grid of (character, ansi_color_escape) tuples.
    """
    rng = random.Random(seed)
    star_chars = ("·", "*", ".", "+", "·", "·", ".")
    star_colors = tuple(f"\033[38;5;{c}m" for c in (240, 245, 250, 255, 243, 238, 248))
    grid: list[list[tuple[str, str]]] = [[(" ", "")] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if rng.random() < 0.02:
                idx = rng.randint(0, len(star_chars) - 1)
                grid[y][x] = (star_chars[idx], star_colors[idx])
    return grid


def generate_planet_art(width: int, height: int) -> list[list[tuple[str, str] | None]]:
    """Generate a quarter-circle planet anchored to bottom-left.

    Args:
        width: Grid width.
        height: Grid height.

    Returns:
        Grid where None = transparent (no planet pixel at that cell).
    """
    radius_x = int(width * 0.35)
    radius_y = int(height * 0.75)

    terrain = (
        ("~", "\033[38;5;27m"),
        ("≈", "\033[38;5;33m"),
        ("~", "\033[38;5;39m"),
        ("%", "\033[38;5;28m"),
        ("#", "\033[38;5;34m"),
        ("∙", "\033[38;5;22m"),
        ("^", "\033[38;5;100m"),
        ("░", "\033[38;5;136m"),
        ("▒", "\033[38;5;94m"),
        ("○", "\033[38;5;255m"),
        ("·", "\033[38;5;252m"),
    )
    limb_color = "\033[38;5;51m"
    glow_color = "\033[38;5;45m"

    grid: list[list[tuple[str, str] | None]] = [[None] * width for _ in range(height)]
    prng = random.Random(42)  # fixed seed — planet is always the same

    for y in range(height):
        for x in range(width):
            dx = x / max(radius_x, 1)
            dy = (height - 1 - y) / max(radius_y, 1)
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > 1.05:
                continue
            if dist > 0.97:
                grid[y][x] = ("│", limb_color)
            elif dist > 0.91:
                grid[y][x] = ("░", glow_color)
            else:
                biome = prng.random()
                if biome < 0.3:
                    idx = prng.randint(0, 2)
                elif biome < 0.55:
                    idx = prng.randint(3, 5)
                elif biome < 0.75:
                    idx = prng.randint(6, 8)
                else:
                    idx = prng.randint(9, 10)
                grid[y][x] = terrain[idx]

    return grid


def generate_stardock_art(width: int, height: int) -> list[list[tuple[str, str] | None]]:
    """Generate a static stardock graphic, right-of-center, slightly elevated.

    Args:
        width: Grid width.
        height: Grid height.

    Returns:
        Grid where None = transparent.
    """
    dock_lines = (
        "    ╥╥    ",
        "  ╔═╩╩═╗  ",
        " ╔╣▪▪▪▪╠╗ ",
        "═╣░░░░░░╠═",
        " ╚╣▪▪▪▪╠╝ ",
        "  ╚════╝  ",
        "    ╨╨    ",
    )
    dock_colors: dict[str, str] = {
        "╥": "\033[38;5;245m", "╨": "\033[38;5;245m", "╩": "\033[38;5;245m",
        "╔": "\033[38;5;250m", "╗": "\033[38;5;250m", "╚": "\033[38;5;250m", "╝": "\033[38;5;250m",
        "═": "\033[38;5;250m", "╣": "\033[38;5;250m", "╠": "\033[38;5;250m",
        "▪": "\033[38;5;39m", "░": "\033[38;5;240m",
    }
    default_color = "\033[38;5;245m"

    start_x = width * 3 // 4
    start_y = height // 4

    grid: list[list[tuple[str, str] | None]] = [[None] * width for _ in range(height)]
    for dy, line in enumerate(dock_lines):
        y = start_y + dy
        if y >= height:
            break
        for dx, ch in enumerate(line):
            x = start_x + dx
            if x >= width:
                break
            if ch != " ":
                grid[y][x] = (ch, dock_colors.get(ch, default_color))

    return grid


def compose_scene(
    width: int,
    height: int,
    port_name: str | None,
    has_planet: bool,
    has_stardock: bool,
    seed: int,
) -> list[list[tuple[str, str]]]:
    """Compose a full sector scene with all layers.

    Args:
        width: Canvas width.
        height: Canvas height.
        port_name: Port name for art generation (None = no port).
        has_planet: Whether to draw the planet.
        has_stardock: Whether to draw the stardock.
        seed: RNG seed for starfield.

    Returns:
        Composed grid of (character, ansi_color_escape) tuples.
    """
    canvas = generate_starfield(width, height, seed)

    if has_planet:
        planet = generate_planet_art(width, height)
        for y in range(height):
            for x in range(width):
                if planet[y][x] is not None:
                    canvas[y][x] = planet[y][x]  # type: ignore[assignment]

    if port_name:
        port_w = min(25, width // 3)
        port_h = min(12, height - 1)
        if port_w > 3 and port_h > 3:
            port_grid = generate_port_art(port_name, port_w, port_h)
            offset_x = (width - port_w) // 2
            if has_planet:
                offset_x = max(offset_x, int(width * 0.35) + 2)
            offset_y = (height - port_h) // 2
            for y in range(port_h):
                for x in range(port_w):
                    char, color = port_grid[y][x]
                    if char != " ":
                        cy, cx = offset_y + y, offset_x + x
                        if 0 <= cy < height and 0 <= cx < width:
                            canvas[cy][cx] = (char, color)

    if has_stardock:
        stardock = generate_stardock_art(width, height)
        for y in range(height):
            for x in range(width):
                if stardock[y][x] is not None:
                    canvas[y][x] = stardock[y][x]  # type: ignore[assignment]

    return canvas
