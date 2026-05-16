#!/usr/bin/env python3
"""PoC: Deterministic ASCII station art generator using WFC-like tile placement.

Usage:
    python tools/station_gen.py "Regel Station"
    python tools/station_gen.py "Trader Vic's" --width 30 --height 15
    python tools/station_gen.py "Port Alpha" --decay 0.3 --symmetry
    python tools/station_gen.py "Stardock" --silhouette spire --density 0.7
    python tools/station_gen.py "Regel Station" --scene
    python tools/station_gen.py --planet
    python tools/station_gen.py --stardock-art
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from dataclasses import dataclass, field
from enum import Enum

# --- Tile System ---

class TileCategory(Enum):
    HULL = "hull"
    FRAME = "frame"
    PIPE = "pipe"
    ANTENNA = "antenna"
    WINDOW = "window"
    DOCK = "dock"
    EMPTY = "empty"


@dataclass(frozen=True)
class Tile:
    char: str
    category: TileCategory
    # Which categories can be adjacent (north, south, east, west)
    north: frozenset[TileCategory]
    south: frozenset[TileCategory]
    east: frozenset[TileCategory]
    west: frozenset[TileCategory]
    # Base weight for selection
    weight: float = 1.0


# Shorthand for building adjacency sets
ALL = frozenset(TileCategory)
SOLID = frozenset({TileCategory.HULL, TileCategory.FRAME, TileCategory.PIPE,
                   TileCategory.WINDOW, TileCategory.DOCK})
STRUCTURAL = frozenset({TileCategory.HULL, TileCategory.FRAME, TileCategory.PIPE,
                        TileCategory.ANTENNA, TileCategory.WINDOW})
EDGE = frozenset({TileCategory.EMPTY, TileCategory.FRAME, TileCategory.DOCK,
                  TileCategory.ANTENNA})

# --- Tile Pack ---

TILES: list[Tile] = [
    # Hull plating — dominant fill (high weight)
    Tile("█", TileCategory.HULL, STRUCTURAL, STRUCTURAL, STRUCTURAL, STRUCTURAL, 3.0),
    Tile("▓", TileCategory.HULL, STRUCTURAL, STRUCTURAL, STRUCTURAL, STRUCTURAL, 2.5),
    Tile("░", TileCategory.HULL, ALL, ALL, ALL, ALL, 2.0),
    # Structural frame — secondary fill
    Tile("╔", TileCategory.FRAME, EDGE, SOLID, SOLID, EDGE, 0.8),
    Tile("╗", TileCategory.FRAME, EDGE, SOLID, EDGE, SOLID, 0.8),
    Tile("╚", TileCategory.FRAME, SOLID, EDGE, SOLID, EDGE, 0.8),
    Tile("╝", TileCategory.FRAME, SOLID, EDGE, EDGE, SOLID, 0.8),
    Tile("═", TileCategory.FRAME, ALL, ALL, SOLID | {TileCategory.FRAME}, SOLID | {TileCategory.FRAME}, 1.5),
    Tile("║", TileCategory.FRAME, SOLID | {TileCategory.FRAME}, SOLID | {TileCategory.FRAME}, ALL, ALL, 1.5),
    # Pipes/conduit — accent runs
    Tile("─", TileCategory.PIPE, ALL, ALL, frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}),
         frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}), 0.5),
    Tile("│", TileCategory.PIPE, frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.ANTENNA}),
         frozenset({TileCategory.PIPE, TileCategory.FRAME, TileCategory.HULL}), ALL, ALL, 0.5),
    Tile("┌", TileCategory.PIPE, EDGE | {TileCategory.HULL}, SOLID, SOLID, EDGE | {TileCategory.HULL}, 0.3),
    Tile("┐", TileCategory.PIPE, EDGE | {TileCategory.HULL}, SOLID, EDGE | {TileCategory.HULL}, SOLID, 0.3),
    Tile("└", TileCategory.PIPE, SOLID, EDGE | {TileCategory.HULL}, SOLID, EDGE | {TileCategory.HULL}, 0.3),
    Tile("┘", TileCategory.PIPE, SOLID, EDGE | {TileCategory.HULL}, EDGE | {TileCategory.HULL}, SOLID, 0.3),
    Tile("┬", TileCategory.PIPE, EDGE, SOLID, SOLID, SOLID, 0.2),
    Tile("┴", TileCategory.PIPE, SOLID, EDGE, SOLID, SOLID, 0.2),
    Tile("├", TileCategory.PIPE, SOLID, SOLID, SOLID, EDGE, 0.2),
    Tile("┤", TileCategory.PIPE, SOLID, SOLID, EDGE, SOLID, 0.2),
    # Antenna/mast — rare accent
    Tile("╥", TileCategory.ANTENNA, EDGE, SOLID, ALL, ALL, 0.1),
    Tile("╨", TileCategory.ANTENNA, SOLID, EDGE, ALL, ALL, 0.1),
    Tile("↑", TileCategory.ANTENNA, EDGE, frozenset({TileCategory.ANTENNA, TileCategory.FRAME, TileCategory.HULL}),
         EDGE, EDGE, 0.08),
    Tile("¤", TileCategory.ANTENNA, EDGE, frozenset({TileCategory.ANTENNA, TileCategory.FRAME}),
         EDGE, EDGE, 0.08),
    # Windows/panels — accent clusters
    Tile("▪", TileCategory.WINDOW, SOLID, SOLID, SOLID, SOLID, 0.4),
    Tile("▫", TileCategory.WINDOW, SOLID, SOLID, SOLID, SOLID, 0.4),
    Tile("[", TileCategory.WINDOW, ALL, ALL, frozenset({TileCategory.WINDOW, TileCategory.HULL}),
         ALL, 0.2),
    Tile("]", TileCategory.WINDOW, ALL, ALL, ALL,
         frozenset({TileCategory.WINDOW, TileCategory.HULL}), 0.2),
    # Docking — rare accent
    Tile(">", TileCategory.DOCK, ALL, ALL, EDGE, SOLID, 0.08),
    Tile("<", TileCategory.DOCK, ALL, ALL, SOLID, EDGE, 0.08),
    Tile("⊏", TileCategory.DOCK, SOLID, SOLID, SOLID, EDGE, 0.06),
    Tile("⊐", TileCategory.DOCK, SOLID, SOLID, EDGE, SOLID, 0.06),
    # Empty (space) — very low weight inside silhouette
    Tile(" ", TileCategory.EMPTY, ALL, ALL, ALL, ALL, 0.1),
]

# --- Color System ---

RESET = "\033[0m"


def _c(n: int) -> str:
    """ANSI 256-color foreground escape."""
    return f"\033[38;5;{n}m"


@dataclass(frozen=True)
class ColorScheme:
    """A base color with shade variation + category-specific accent colors."""
    base_shades: list[int]       # 3-5 shades for hull/frame (dominant ~60%)
    pipe_accents: list[int]      # 2-3 colors for pipes/conduit
    window_accents: list[int]    # 2-3 colors for windows/panels
    antenna_accents: list[int]   # 1-2 colors for antenna/mast tips
    dock_accents: list[int]      # 1-2 colors for docking elements


# Base hue families — each has shade variations + complementary accents
BASE_HUES: list[dict[str, list[int]]] = [
    {  # Steel/gray base — cyan windows, yellow pipes, red antenna
        "base": [240, 243, 245, 248, 250],
        "pipe": [178, 220, 136],
        "window": [39, 45, 51],
        "antenna": [196, 203],
        "dock": [255, 252],
    },
    {  # Dark blue base — cyan windows, orange pipes, white antenna
        "base": [17, 18, 19, 20, 24],
        "pipe": [166, 172, 208],
        "window": [45, 51, 87],
        "antenna": [255, 231],
        "dock": [39, 45],
    },
    {  # Warm gray base — green windows, copper pipes, blue antenna
        "base": [236, 238, 240, 243, 245],
        "pipe": [130, 166, 172],
        "window": [28, 34, 40],
        "antenna": [39, 75],
        "dock": [178, 220],
    },
    {  # Dark green base — yellow windows, white pipes, red antenna
        "base": [22, 23, 28, 29, 34],
        "pipe": [250, 252, 255],
        "window": [220, 226, 228],
        "antenna": [196, 160],
        "dock": [45, 51],
    },
    {  # Purple/dark base — magenta windows, cyan pipes, gold antenna
        "base": [53, 54, 55, 56, 57],
        "pipe": [37, 43, 44],
        "window": [163, 169, 201],
        "antenna": [220, 178],
        "dock": [255, 252],
    },
    {  # Rust/brown base — blue windows, yellow pipes, white antenna
        "base": [94, 95, 130, 131, 137],
        "pipe": [178, 214, 220],
        "window": [39, 45, 75],
        "antenna": [255, 231],
        "dock": [166, 172],
    },
    {  # Teal base — orange windows, white pipes, magenta antenna
        "base": [23, 29, 30, 36, 37],
        "pipe": [250, 252, 255],
        "window": [166, 172, 208],
        "antenna": [201, 163],
        "dock": [220, 226],
    },
    {  # Charcoal base — red windows, blue pipes, green antenna
        "base": [233, 235, 237, 239, 241],
        "pipe": [33, 39, 69],
        "window": [124, 160, 196],
        "antenna": [34, 40],
        "dock": [245, 250],
    },
]


def make_color_scheme(seed: int, palette_name: str | None = None) -> ColorScheme:
    """Build a color scheme from the seed (or override with palette name)."""
    if palette_name:
        # Map old palette names to base hues for backward compat
        name_map = {"steel": 0, "ice": 1, "military": 3, "copper": 5,
                    "plasma": 4, "rust": 5, "gold": 5, "neon": 6}
        idx = name_map.get(palette_name, seed % len(BASE_HUES))
    else:
        idx = seed % len(BASE_HUES)

    hue = BASE_HUES[idx]

    # Use more seed bits to pick shade sub-selections and rotate accents
    rotation = (seed >> 8) % 3

    # Rotate accent lists for extra variation between ports with same base
    def rotate_list(lst: list[int], n: int) -> list[int]:
        if not lst:
            return lst
        n = n % len(lst)
        return lst[n:] + lst[:n]

    return ColorScheme(
        base_shades=hue["base"],
        pipe_accents=rotate_list(hue["pipe"], rotation),
        window_accents=rotate_list(hue["window"], rotation),
        antenna_accents=rotate_list(hue["antenna"], rotation),
        dock_accents=rotate_list(hue["dock"], rotation),
    )


def color_for_tile(tile: Tile, x: int, y: int, scheme: ColorScheme, rng: random.Random) -> str:
    """Pick a color for a tile based on its category, position, and the scheme."""
    if tile.char == " ":
        return ""

    if tile.category == TileCategory.HULL:
        # Base shades with positional variation
        shade_idx = (x * 3 + y * 7 + rng.randint(0, 1)) % len(scheme.base_shades)
        return _c(scheme.base_shades[shade_idx])

    elif tile.category == TileCategory.FRAME:
        # Mostly base, occasionally brighter
        if rng.random() < 0.3:
            return _c(scheme.base_shades[-1])  # brightest base shade
        shade_idx = (x + y * 5) % len(scheme.base_shades)
        return _c(scheme.base_shades[shade_idx])

    elif tile.category == TileCategory.PIPE:
        accent_idx = (x * 2 + y) % len(scheme.pipe_accents)
        return _c(scheme.pipe_accents[accent_idx])

    elif tile.category == TileCategory.WINDOW:
        accent_idx = (x + y * 3) % len(scheme.window_accents)
        return _c(scheme.window_accents[accent_idx])

    elif tile.category == TileCategory.ANTENNA:
        accent_idx = (x + y) % len(scheme.antenna_accents)
        return _c(scheme.antenna_accents[accent_idx])

    elif tile.category == TileCategory.DOCK:
        accent_idx = (x + y) % len(scheme.dock_accents)
        return _c(scheme.dock_accents[accent_idx])

    return _c(scheme.base_shades[0])

# --- Silhouette Masks ---

class Silhouette(Enum):
    TOWER = "tower"
    DOME = "dome"
    SPIRE = "spire"
    WIDE = "wide"
    CROSS = "cross"
    DIAMOND = "diamond"


def make_silhouette(shape: Silhouette, width: int, height: int) -> list[list[bool]]:
    """Generate a boolean mask for where tiles can be placed."""
    mask = [[False] * width for _ in range(height)]
    cx = width // 2
    cy = height // 2

    if shape == Silhouette.TOWER:
        # Narrow tall rectangle with slight taper at top
        for y in range(height):
            taper = max(0, (height - y - 1) * width // (height * 4))
            left = cx - width // 4 + taper
            right = cx + width // 4 - taper
            for x in range(max(0, left), min(width, right + 1)):
                mask[y][x] = True

    elif shape == Silhouette.DOME:
        # Semicircle on top of a rectangle
        base_top = height // 2
        radius = width // 3
        for y in range(height):
            if y >= base_top:
                # Rectangle base
                left = cx - width // 3
                right = cx + width // 3
            else:
                # Dome arc
                dy = base_top - y
                if dy <= radius:
                    half_w = int((radius**2 - dy**2) ** 0.5)
                    left = cx - half_w
                    right = cx + half_w
                else:
                    continue
            for x in range(max(0, left), min(width, right + 1)):
                mask[y][x] = True

    elif shape == Silhouette.SPIRE:
        # Triangle pointing up
        for y in range(height):
            progress = y / max(height - 1, 1)
            half_w = int(progress * width // 2.5)
            for x in range(cx - half_w, cx + half_w + 1):
                if 0 <= x < width:
                    mask[y][x] = True

    elif shape == Silhouette.WIDE:
        # Wide rectangle, shorter
        for y in range(height // 4, height * 3 // 4):
            for x in range(width // 6, width * 5 // 6):
                mask[y][x] = True

    elif shape == Silhouette.CROSS:
        # Plus/cross shape
        arm_w = width // 5
        arm_h = height // 5
        for y in range(height):
            for x in range(width):
                in_vert = abs(x - cx) <= arm_w
                in_horiz = abs(y - cy) <= arm_h
                if in_vert or in_horiz:
                    mask[y][x] = True

    elif shape == Silhouette.DIAMOND:
        # Diamond/rhombus
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

# Border characters based on which sides are exposed to space
# Key: frozenset of exposed directions -> character
EDGE_CHARS: dict[frozenset[str], str] = {
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

# Diagonal edge characters for sloped boundaries
# When a cell has diagonal exposure (corner neighbor out but cardinal neighbors in)
DIAG_CHARS: dict[str, str] = {
    "NE": "╮",
    "NW": "╭",
    "SE": "╯",
    "SW": "╰",
}


def detect_edges(mask: list[list[bool]], width: int, height: int) -> list[list[frozenset[str] | None]]:
    """For each cell in the mask, determine which sides are exposed to empty space.

    Returns a grid where each cell is either None (interior/outside) or a frozenset
    of exposed directions.
    """
    edges: list[list[frozenset[str] | None]] = [[None] * width for _ in range(height)]

    for y in range(height):
        for x in range(width):
            if not mask[y][x]:
                continue

            exposed: set[str] = set()
            # Check cardinal neighbors
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


def get_edge_char(exposed: frozenset[str], x: int, y: int, mask: list[list[bool]],
                  width: int, height: int) -> str:
    """Pick the right edge character, considering diagonal slopes."""
    # For single-direction exposure on diagonal silhouettes, check if it's a slope
    if len(exposed) == 1:
        direction = next(iter(exposed))
        if direction in ("N", "S"):
            # Check if this is a diagonal slope (neighbor row is narrower)
            check_y = y - 1 if direction == "N" else y + 1
            if 0 <= check_y < height:
                # Is the cell to our east/west also an edge on the same side?
                left_out = x > 0 and not mask[check_y][x - 1] and mask[y][x - 1]
                right_out = x < width - 1 and not mask[check_y][x + 1] and mask[y][x + 1]
                if left_out and not right_out:
                    return "/" if direction == "N" else "\\"
                if right_out and not left_out:
                    return "\\" if direction == "N" else "/"

    return EDGE_CHARS.get(exposed, "█")


# --- WFC-like Generator ---

@dataclass
class GeneratorConfig:
    width: int = 25
    height: int = 12
    decay: float = 0.4
    density: float = 0.6
    symmetry: bool = True
    silhouette: Silhouette = Silhouette.TOWER
    palette_name: str | None = None
    outline: bool = True  # Hard edge on the silhouette boundary


@dataclass
class RunTracker:
    """Tracks run lengths per category per direction at each cell."""
    horizontal: list[list[dict[TileCategory, int]]] = field(default_factory=list)
    vertical: list[list[dict[TileCategory, int]]] = field(default_factory=list)

    def init(self, width: int, height: int) -> None:
        self.horizontal = [[{} for _ in range(width)] for _ in range(height)]
        self.vertical = [[{} for _ in range(width)] for _ in range(height)]


def generate_station(name: str, config: GeneratorConfig) -> list[list[tuple[str, str]]]:
    """Generate station art. Returns grid of (character, ansi_color) tuples."""
    # Seed from name hash
    h = hashlib.sha256(name.encode()).hexdigest()
    seed = int(h[:16], 16)
    rng = random.Random(seed)

    # Build color scheme from seed
    scheme = make_color_scheme(seed, config.palette_name)

    # Derive silhouette variation from hash (slight randomization of the mask)
    mask = make_silhouette(config.silhouette, config.width, config.height)

    # Effective width for generation (half if symmetric)
    gen_width = (config.width + 1) // 2 if config.symmetry else config.width

    # Initialize grid
    grid: list[list[Tile | None]] = [[None] * gen_width for _ in range(config.height)]
    runs = RunTracker()
    runs.init(gen_width, config.height)

    # Collapse order: top-to-bottom, left-to-right
    for y in range(config.height):
        for x in range(gen_width):
            # Check if this cell is within the silhouette
            # For symmetric generation, mirror the mask check
            mask_x = x if not config.symmetry else x
            mirror_x = config.width - 1 - x if config.symmetry else x

            in_mask = mask[y][mask_x] if mask_x < config.width else False
            if config.symmetry:
                in_mask = in_mask or (mirror_x < config.width and mask[y][mirror_x])

            if not in_mask:
                grid[y][x] = Tile(" ", TileCategory.EMPTY, ALL, ALL, ALL, ALL)
                continue

            # Gather constraints from neighbors
            valid_categories: set[TileCategory] = set(TileCategory)

            # North neighbor
            if y > 0 and grid[y - 1][x] is not None:
                north_tile = grid[y - 1][x]
                valid_categories &= north_tile.south

            # West neighbor
            if x > 0 and grid[y][x - 1] is not None:
                west_tile = grid[y][x - 1]
                valid_categories &= west_tile.east

            if not valid_categories:
                valid_categories = {TileCategory.HULL, TileCategory.EMPTY}

            # Filter tiles by valid categories
            candidates = [t for t in TILES if t.category in valid_categories]
            if not candidates:
                candidates = [t for t in TILES if t.category == TileCategory.HULL]

            # Determine neighbor categories for momentum
            neighbor_cats: list[TileCategory] = []
            if y > 0 and grid[y - 1][x] is not None:
                neighbor_cats.append(grid[y - 1][x].category)
            if x > 0 and grid[y][x - 1] is not None:
                neighbor_cats.append(grid[y][x - 1].category)

            # Apply weights with momentum and decay
            weights = []
            for tile in candidates:
                w = tile.weight

                # Momentum: strongly boost tiles matching neighbor categories
                # This creates coherent zones instead of noise
                matching_neighbors = sum(1 for nc in neighbor_cats if nc == tile.category)
                if matching_neighbors > 0:
                    w *= 3.0 * matching_neighbors  # strong continuation bias

                # Run-length decay (only kicks in after momentum builds runs)
                if x > 0:
                    h_run = runs.horizontal[y][x - 1].get(tile.category, 0)
                    if h_run > 2:  # allow short runs before decay starts
                        w *= (1 - config.decay) ** (h_run - 2)

                if y > 0:
                    v_run = runs.vertical[y - 1][x].get(tile.category, 0)
                    if v_run > 2:
                        w *= (1 - config.decay) ** (v_run - 2)

                # Density control: penalize empty inside silhouette
                if tile.category == TileCategory.EMPTY:
                    w *= (1 - config.density) * 0.5
                else:
                    w *= config.density

                weights.append(max(w, 0.01))

            # Weighted random selection
            chosen = rng.choices(candidates, weights=weights, k=1)[0]
            grid[y][x] = chosen

            # Update run tracking
            if x > 0:
                prev_h = runs.horizontal[y][x - 1].get(chosen.category, 0)
                runs.horizontal[y][x][chosen.category] = prev_h + 1 if chosen.category in runs.horizontal[y][x - 1] or prev_h > 0 else 1
            else:
                runs.horizontal[y][x][chosen.category] = 1

            if y > 0:
                prev_v = runs.vertical[y - 1][x].get(chosen.category, 0)
                runs.vertical[y][x][chosen.category] = prev_v + 1 if chosen.category in runs.vertical[y - 1][x] or prev_v > 0 else 1
            else:
                runs.vertical[y][x][chosen.category] = 1

    # Edge detection on the full-width mask
    if config.outline:
        edge_map = detect_edges(mask, config.width, config.height)
    else:
        edge_map = [[None] * config.width for _ in range(config.height)]

    # Expand to full width (mirror if symmetric)
    full_grid: list[list[tuple[str, str]]] = []
    color_rng = random.Random(seed + 1)  # separate RNG for color so structure isn't affected
    # Edge color: brightest base shade
    edge_color = _c(scheme.base_shades[-1])

    for y in range(config.height):
        row: list[tuple[str, str]] = []
        for x in range(config.width):
            # Check if this is an edge cell
            exposed = edge_map[y][x]
            if config.outline and exposed:
                char = get_edge_char(exposed, x, y, mask, config.width, config.height)
                row.append((char, edge_color))
                continue

            if config.symmetry:
                src_x = x if x < gen_width else config.width - 1 - x
                tile = grid[y][src_x]
            else:
                tile = grid[y][x] if x < gen_width else None

            if tile is None:
                row.append((" ", ""))
            else:
                # Get color from the new scheme
                color = color_for_tile(tile, x, y, scheme, color_rng)

                # Mirror certain characters
                char = tile.char
                if config.symmetry and x >= gen_width:
                    mirror_map = {"╔": "╗", "╗": "╔", "╚": "╝", "╝": "╚",
                                  "┌": "┐", "┐": "┌", "└": "┘", "┘": "└",
                                  "├": "┤", "┤": "├", ">": "<", "<": ">",
                                  "⊏": "⊐", "⊐": "⊏", "[": "]", "]": "["}
                    char = mirror_map.get(char, char)

                row.append((char, color))
        full_grid.append(row)

    return full_grid


def render(grid: list[list[tuple[str, str]]], no_color: bool = False) -> str:
    """Render grid to string with ANSI colors."""
    lines = []
    for row in grid:
        parts = []
        for char, color in row:
            if no_color or not color:
                parts.append(char)
            else:
                parts.append(f"{color}{char}{RESET}")
        lines.append("".join(parts))
    return "\n".join(lines)


# --- Static Art: Planet, Stardock, Starfield ---

def generate_starfield(width: int, height: int, rng: random.Random) -> list[list[tuple[str, str]]]:
    """Generate a sparse starfield background."""
    star_chars = ["·", "*", ".", "+", "·", "·", "."]
    star_colors = [_c(240), _c(245), _c(250), _c(255), _c(243), _c(238), _c(248)]
    grid: list[list[tuple[str, str]]] = [[(" ", "")] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if rng.random() < 0.02:
                idx = rng.randint(0, len(star_chars) - 1)
                grid[y][x] = (star_chars[idx], star_colors[idx])
    return grid


def generate_planet(width: int, height: int) -> list[list[tuple[str, str] | None]]:
    """Generate a quarter-circle planet anchored to bottom-left.

    Returns grid where None = transparent.
    """
    radius_x = int(width * 0.35)
    radius_y = int(height * 0.75)

    terrain = [
        ("~", _c(27)),   # deep ocean
        ("≈", _c(33)),   # ocean
        ("~", _c(39)),   # shallow water
        ("%", _c(28)),   # forest
        ("#", _c(34)),   # jungle
        ("∙", _c(22)),   # plains
        ("^", _c(100)),  # mountains
        ("░", _c(136)),  # desert
        ("▒", _c(94)),   # badlands
        ("○", _c(255)),  # clouds
        ("·", _c(252)),  # thin clouds
    ]

    limb_color = _c(51)   # bright cyan atmosphere
    glow_color = _c(45)

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
    """Generate a static stardock graphic, right-of-center, slightly elevated."""
    dock_lines = [
        "    ╥╥    ",
        "  ╔═╩╩═╗  ",
        " ╔╣▪▪▪▪╠╗ ",
        "═╣░░░░░░╠═",
        " ╚╣▪▪▪▪╠╝ ",
        "  ╚════╝  ",
        "    ╨╨    ",
    ]

    dock_colors: dict[str, str] = {
        "╥": _c(245), "╨": _c(245), "╩": _c(245),
        "╔": _c(250), "╗": _c(250), "╚": _c(250), "╝": _c(250),
        "═": _c(250), "╣": _c(250), "╠": _c(250),
        "▪": _c(39), "░": _c(240),
    }

    # Position: far right, slightly above center
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
                grid[y][x] = (ch, dock_colors.get(ch, _c(245)))

    return grid


def compose_scene(
    width: int, height: int,
    port_name: str | None = None,
    has_planet: bool = False,
    has_stardock: bool = False,
    no_color: bool = False,
) -> str:
    """Compose a full scene: starfield + optional planet, port, stardock."""
    rng = random.Random(7777)
    canvas = generate_starfield(width, height, rng)

    # Planet (bottom-left)
    if has_planet:
        planet = generate_planet(width, height)
        for y in range(height):
            for x in range(width):
                if planet[y][x] is not None:
                    canvas[y][x] = planet[y][x]

    # Port (center, offset right if planet present)
    if port_name:
        h = hashlib.sha256(port_name.encode()).hexdigest()
        seed = int(h[:16], 16)
        port_w = min(25, width // 3)
        port_h = min(12, height - 1)
        config = GeneratorConfig(
            width=port_w, height=port_h, decay=0.4,
            density=0.3 + ((seed >> 16) % 100) / 100.0 * 0.7,
            symmetry=(seed % 10) < 7,
            silhouette=list(Silhouette)[seed % len(Silhouette)],
            outline=True,
        )
        port_grid = generate_station(port_name, config)

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

    # Stardock (right, slightly up)
    if has_stardock:
        stardock = generate_stardock_art(width, height)
        for y in range(height):
            for x in range(width):
                if stardock[y][x] is not None:
                    canvas[y][x] = stardock[y][x]

    return render(canvas, no_color=no_color)


# --- CLI ---

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic ASCII station art from a port name.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("name", nargs="?", default=None, help="Port/station name (used as hash seed)")
    parser.add_argument("-W", "--width", type=int, default=25, help="Art width in chars (default: 25)")
    parser.add_argument("-H", "--height", type=int, default=12, help="Art height in rows (default: 12)")
    parser.add_argument("-d", "--decay", type=float, default=0.4,
                        help="Run-length decay rate 0.0-1.0 (default: 0.4). Higher = shorter runs.")
    parser.add_argument("-D", "--density", type=float, default=None,
                        help="Fill density 0.3-1.0 (default: hash-determined)")
    parser.add_argument("-s", "--symmetry", action="store_true", default=False,
                        help="Force bilateral symmetry (default: off, hash-determined)")
    parser.add_argument("-S", "--no-symmetry", action="store_true", default=False,
                        help="Force asymmetry")
    parser.add_argument("--silhouette", choices=[s.value for s in Silhouette], default=None,
                        help="Silhouette shape (default: hash-determined)")
    parser.add_argument("-p", "--palette", choices=["steel", "ice", "military", "copper", "plasma", "rust", "gold", "neon"],
                        default=None, help="Color base hue (default: hash-determined)")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")
    parser.add_argument("--no-outline", action="store_true", help="Disable hard edge outline")
    parser.add_argument("--all-silhouettes", action="store_true",
                        help="Show the name rendered with all silhouette shapes")
    parser.add_argument("--all-palettes", action="store_true",
                        help="Show the name rendered with all color palettes")
    parser.add_argument("--scene", action="store_true",
                        help="Render full composed scene (starfield + planet + port + stardock)")
    parser.add_argument("--planet", action="store_true",
                        help="Show planet art only")
    parser.add_argument("--stardock-art", action="store_true",
                        help="Show stardock art only")
    parser.add_argument("--scene-width", type=int, default=80,
                        help="Scene canvas width (default: 80)")
    parser.add_argument("--scene-height", type=int, default=14,
                        help="Scene canvas height (default: 14)")

    args = parser.parse_args()

    # Scene/planet/stardock modes (don't require a name)
    if args.planet:
        w, h = args.scene_width, args.scene_height
        canvas = generate_starfield(w, h, random.Random(7777))
        planet = generate_planet(w, h)
        for y in range(h):
            for x in range(w):
                if planet[y][x] is not None:
                    canvas[y][x] = planet[y][x]
        print(f"\n{'─' * 40}")
        print("  Planet (quarter-circle, bottom-left)")
        print(f"{'─' * 40}")
        print(render(canvas, no_color=args.no_color))
        print()
        return

    if args.stardock_art:
        w, h = args.scene_width, args.scene_height
        canvas = generate_starfield(w, h, random.Random(7777))
        stardock = generate_stardock_art(w, h)
        for y in range(h):
            for x in range(w):
                if stardock[y][x] is not None:
                    canvas[y][x] = stardock[y][x]
        print(f"\n{'─' * 40}")
        print("  Stardock (static, right-of-center)")
        print(f"{'─' * 40}")
        print(render(canvas, no_color=args.no_color))
        print()
        return

    if not args.name:
        parser.error("name is required (unless using --planet or --stardock-art)")

    if args.scene:
        w, h = args.scene_width, args.scene_height
        print(f"\n{'─' * w}")
        print(f"  Full scene: {args.name} + planet + stardock")
        print(f"{'─' * w}")
        print(compose_scene(w, h, port_name=args.name, has_planet=True,
                            has_stardock=True, no_color=args.no_color))
        print()
        # Also show without planet/stardock for comparison
        print(f"{'─' * w}")
        print(f"  Port only: {args.name}")
        print(f"{'─' * w}")
        print(compose_scene(w, h, port_name=args.name, has_planet=False,
                            has_stardock=False, no_color=args.no_color))
        print()
        # Empty sector (starfield only)
        print(f"{'─' * w}")
        print("  Empty sector (starfield only)")
        print(f"{'─' * w}")
        print(compose_scene(w, h, port_name=None, has_planet=False,
                            has_stardock=False, no_color=args.no_color))
        print()
        return

    # Determine symmetry
    h = hashlib.sha256(args.name.encode()).hexdigest()
    seed = int(h[:16], 16)

    if args.symmetry:
        symmetry = True
    elif args.no_symmetry:
        symmetry = False
    else:
        # Hash-determined: ~70% chance of symmetry (stations usually look symmetric)
        symmetry = (seed % 10) < 7

    # Determine silhouette
    if args.silhouette:
        silhouette = Silhouette(args.silhouette)
    else:
        silhouettes = list(Silhouette)
        silhouette = silhouettes[seed % len(silhouettes)]

    # Determine density from hash: range [0.3, 1.0]
    if args.density is not None:
        density = args.density
    else:
        density = 0.3 + ((seed >> 16) % 100) / 100.0 * 0.7

    config = GeneratorConfig(
        width=args.width,
        height=args.height,
        decay=args.decay,
        density=density,
        symmetry=symmetry,
        silhouette=silhouette,
        palette_name=args.palette,
        outline=not args.no_outline,
    )

    if args.all_silhouettes:
        for s in Silhouette:
            cfg = GeneratorConfig(
                width=config.width, height=config.height,
                decay=config.decay, density=config.density,
                symmetry=config.symmetry, silhouette=s,
                palette_name=config.palette_name,
                outline=config.outline,
            )
            print(f"\n{'─' * 40}")
            print(f"  {args.name} — silhouette: {s.value}")
            print(f"{'─' * 40}")
            grid = generate_station(args.name, cfg)
            print(render(grid, no_color=args.no_color))
        return

    if args.all_palettes:
        palette_names = ["steel", "ice", "military", "copper", "plasma", "rust", "gold", "neon"]
        for p_name in palette_names:
            cfg = GeneratorConfig(
                width=config.width, height=config.height,
                decay=config.decay, density=config.density,
                symmetry=config.symmetry, silhouette=config.silhouette,
                palette_name=p_name,
                outline=config.outline,
            )
            print(f"\n{'─' * 40}")
            print(f"  {args.name} — palette: {p_name}")
            print(f"{'─' * 40}")
            grid = generate_station(args.name, cfg)
            print(render(grid, no_color=args.no_color))
        return

    # Single generation
    print(f"\n{'─' * 40}")
    print(f"  {args.name}")
    print(f"  silhouette: {silhouette.value} | symmetry: {symmetry} | decay: {args.decay} | density: {density:.2f}")
    print(f"{'─' * 40}")
    grid = generate_station(args.name, config)
    print(render(grid, no_color=args.no_color))
    print()


if __name__ == "__main__":
    main()
