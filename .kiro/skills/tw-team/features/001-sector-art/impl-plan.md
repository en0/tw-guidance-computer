# Implementation Plan: Sector Art

## Overview
Add deterministic ASCII art to the HUD showing sector contents (port, planet, stardock, starfield). Port art is generated via WFC-like tile placement seeded by port name hash. Planet and stardock are static designs. A CLI command renders sector art for previously visited sectors.

## Work Units

### Unit 1: Domain — Planet Model
- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/models.py`
- **Description**: Add a `Planet` frozen dataclass with `sector_id: int`, `name: str`, `planet_class: str`.
- **Dependencies**: None.
- **Tests**: `tests/test_domain/test_models.py` — construction, frozen validation.

### Unit 2: Port — Planet Storage
- **Layer**: application/ports
- **Files**: `src/tw_guidance_computer/application/ports/game_state_store.py`
- **Description**: Add `upsert_planet(planet: Planet) -> None` and `has_planet(sector_id: int) -> bool` to the `GameStateStore` Protocol.
- **Dependencies**: Unit 1 (Planet model).
- **Tests**: None (Protocol definition only — tested via adapter).

### Unit 3: Adapter — SQLite Planet Storage
- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/sqlite_store.py`
- **Description**: Add `planets` table to schema. Implement `upsert_planet` and `has_planet` on `SqliteGameStateStore`.
- **Dependencies**: Unit 2 (port definition).
- **Tests**: `tests/test_adapters/test_sqlite_store.py` — upsert, has_planet true/false, multiple planets per sector.

### Unit 4: Parser — Planet Detection
- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/parse_log_chunk.py`
- **Description**: Add planet regex `r"Planets?\s*:\s*\(([A-Z])\)\s*(.+)"`. After matching, call `self._store.upsert_planet(Planet(sector_id=self._current_sector, name=name, planet_class=cls))`. Placed in `_extract_sectors_and_warps` after port detection (planet line follows port line in sector display).
- **Dependencies**: Unit 2 (port method available).
- **Tests**: `tests/test_application/test_parse_log_chunk.py` — planet detected, associated with correct sector, multiple planets, no false matches.

### Unit 5: Domain — Art Generation
- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/sector_art.py`
- **Description**: Pure domain module containing the art generation logic (no I/O). Functions:
  - `generate_port_art(name: str, width: int, height: int) -> list[list[tuple[str, str]]]` — WFC tile placement from `tools/station_gen.py`
  - `generate_planet_art(width: int, height: int) -> list[list[tuple[str, str] | None]]` — static planet
  - `generate_stardock_art(width: int, height: int) -> list[list[tuple[str, str] | None]]` — static stardock
  - `generate_starfield(width: int, height: int, seed: int) -> list[list[tuple[str, str]]]` — background
  - `compose_scene(width: int, height: int, port_name: str | None, has_planet: bool, has_stardock: bool, seed: int) -> list[list[tuple[str, str]]]` — layer composition
  All pure functions, deterministic, no I/O. Uses only stdlib (`hashlib`, `random`, `re`, `dataclasses`).
- **Dependencies**: None (pure domain logic).
- **Tests**: `tests/test_domain/test_sector_art.py` — determinism (same input = same output), correct dimensions, planet/stardock placement, empty scene is starfield only.

### Unit 6: Use Case — Render Sector Art
- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/render_sector_art.py`
- **Description**: Use case `RenderSectorArt` with `execute(sector_id: int, width: int, height: int) -> list[list[tuple[str, str]]]`. Queries store for port name, planet presence, stardock (port_class == 0). Calls domain art generation. Returns composed grid.
- **Dependencies**: Unit 2 (has_planet port), Unit 5 (art generation).
- **Tests**: `tests/test_application/test_render_sector_art.py` — mock store, verify correct composition for port+planet, port-only, empty sector, stardock detection.

### Unit 7: Adapter — HUD Art Panel
- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/tui.py`
- **Description**: Add `_render_art_panel` method to `HudDisplay`. Called from `_render` after the two-column area. Caches art grid (regenerates only on sector change or resize). Renders using curses 256-color pairs. Graceful degradation: skip if terminal < 25 rows.
- **Dependencies**: Unit 6 (use case).
- **Tests**: Integration test — verify panel renders without crash at various terminal sizes. (Curses testing is limited; focus on unit testing the use case and domain.)

### Unit 8: Adapter — CLI sector-art Command
- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/cli_commands.py`, `src/tw_guidance_computer/cli.py`
- **Description**: Add `sector_art(sector_id: int)` method to `CliAdapter`. Checks sector is explored, queries store, calls `RenderSectorArt`, prints with ANSI color to stdout. Register `sector-art` subcommand in `cli.py`.
- **Dependencies**: Unit 6 (use case).
- **Tests**: `tests/test_adapters/test_cli_commands.py` — unexplored sector error, renders output for visited sector.

## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A (parallel) | Unit 1, Unit 5 | No shared files. Domain model + art generation are independent. |
| B (after A) | Unit 2, Unit 4 | Unit 2 needs Unit 1. Unit 4 needs Unit 2. Can start Unit 2 immediately after Unit 1. |
| C (after A) | Unit 3 | Needs Unit 2 (port definition). |
| D (after A, B) | Unit 6 | Needs Unit 2 (port) + Unit 5 (art generation). |
| E (after D) | Unit 7, Unit 8 | Both need Unit 6. Can run in parallel (different files). |

Realistic execution: A → B+C → D → E

## New Domain Types
- `Planet` — frozen dataclass: `sector_id: int`, `name: str`, `planet_class: str`

## New Ports
- `GameStateStore.upsert_planet(planet: Planet) -> None`
- `GameStateStore.has_planet(sector_id: int) -> bool`

## New Use Cases
- `RenderSectorArt` — orchestrates store queries + domain art generation

## Adapter Changes
- `SqliteGameStateStore`: new `planets` table, implement `upsert_planet` and `has_planet`
- `ParseLogChunk`: add planet regex in `_extract_sectors_and_warps`
- `HudDisplay`: add `_render_art_panel` method, cache management, graceful degradation
- `CliAdapter`: add `sector_art` method
- `cli.py`: register `sector-art` subcommand

## Risk Notes
- **Curses 256-color**: The HUD currently uses basic curses color pairs (1–5). The art panel needs 256-color support. Curses supports this via `curses.init_color` or by writing raw ANSI escapes within `addstr`. May need to use `addstr` with raw ANSI codes rather than curses color pairs for the art panel specifically.
- **Performance**: WFC generation for a 25×12 grid is fast (~1ms). Caching per sector change means no performance concern on the 250ms refresh loop.
- **Terminal compatibility**: 256-color requires `TERM` supporting it (user has `st-256color`). Fallback: if 256-color unavailable, render art in basic 8 colors.
