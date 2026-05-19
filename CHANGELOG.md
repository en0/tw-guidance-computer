# Changelog

## 0.5.0

### New Features

- **Safe Harbor RED ALERT**: When turns drop below threshold (default 50), a centered overlay shows the fastest BFS route to the nearest safe sector (Federation space or StarDock)
  - Three overlay states: route found, already safe, no known route ("Uhoh, I think you're in trouble.")
  - Auto-clears when turns recover above threshold — no manual dismissal
  - Route recalculates on sector change (cached between changes)
- **`tw safe-harbor`**: CLI command to check nearest safe sector and route on demand, regardless of turn count
- **Turn warning color adjustment**: Yellow at 200 turns, yellow+reverse at 100–199, red below 100
- **Configurable thresholds**: `turn_warning_yellow`, `turn_warning_red`, `turn_alert_threshold` in config.ini, overridable per-profile

### Architecture

- New domain models: `SafeHarborRoute`, `TurnThresholds` (frozen dataclasses with validation)
- New use case: `FindSafeHarbor` — BFS to nearest Federation/StarDock sector
- New port method: `get_safe_sector_ids()` on `GameStateStore`
- New helper: `format_alert_overlay()` — pure function for testable overlay content generation
- Composition root consolidated: `resolve_config()` constructs `IniProfileStore` once for both db_path and thresholds

## 0.4.0

### New Features

- **Profile-based configuration**: Named profiles replace the `--db` flag for managing multiple servers
  - Config file at `~/.config/tw-guidance-computer/config.ini` (plain INI, editable with any text editor)
  - `tw profile create <name>` — create a new profile with auto-generated DB path
  - `tw profile list` — list all profiles, marking the default with `*`
  - `--profile / -p` flag on both `tw` and `tw-hud` to select a profile
  - `--create` flag on `tw-hud` for inline profile creation when starting a new server
  - Default profile used automatically when no `--profile` specified
  - Auto-migration on first run: creates config pointing to existing DB — no data loss on upgrade
- **`--db` flag removed** from both `tw` and `tw-hud`
- **Migration guide**: [docs/migration-from-db-flag.md](docs/migration-from-db-flag.md) for users transitioning from `--db`

### Fixes

- `ValidationError` from malformed config now caught cleanly in CLI (no traceback)

### Architecture

- New domain models: `Profile`, `ProfileListing` (frozen dataclasses with validation)
- New domain exceptions: `ProfileNotFoundError`, `ProfileExistsError`, `ConfigError`
- New port: `ProfileStore` protocol (abstracts config file I/O)
- New adapter: `IniProfileStore` (configparser-based, `[profile:name]` namespaced sections)
- New use cases: `CreateProfile`, `ListProfiles`
- Composition root resolves profile → discrete `db_path: Path` passed downstream (no config god object)

## 0.3.1

### Architecture

- **Mechanical architecture gates**: 13 boolean gates verify structural correctness on every commit
  - Domain value objects validate invariants unconditionally
  - Layer import rule enforced by AST analysis
  - Exception boundaries verified at both adapter directions (inbound and outbound)
- **Adapter split**: adapters/inbound/ and adapters/outbound/ replace flat adapter directory
- **UseCases container moved to application layer**
- **Untyped dicts replaced with proper dataclasses**
- **All type: ignore comments eliminated from domain and application code**

## 0.3.0

### New Features

- **Sector Art**: Deterministic ASCII art in the HUD showing sector contents at a glance
  - Port art generated via WFC-like tile placement, seeded by port name hash — same station looks the same for every player
  - Planet shown as a quarter-circle in the bottom-left (static design)
  - Stardock shown as a small structure on the right (static design, conveys distance)
  - Empty sectors display a starfield background
  - Multiple elements compose together: starfield → planet → port → stardock
  - 256-color support with seed-determined color schemes per station
  - Art panel cached per sector, regenerates on sector change or terminal resize
  - Graceful degradation: hidden on terminals < 25 rows
- **`tw sector-art <sector_id>`**: CLI command to view sector art for previously visited sectors
- **Planet detection**: Parser now extracts planet presence from sector displays (`Planets : (M) Terra`)

### Architecture

- New domain model: `Planet` (frozen dataclass with validation)
- New use case: `RenderSectorArt` — orchestrates store queries + domain art generation
- New port methods: `upsert_planet`, `has_planet` on `GameStateStore`
- New SQLite table: `planets` (sector_id, name, planet_class)
- HUD layout: two-column area fixed at 12 rows, art panel fills remaining space above footer

## 0.2.0

### Parser Accuracy

- **Sync points**: Parse `<Info>` block and compact status bar as authoritative state resets for sector, turns, credits, holds, and cargo
- **Turn counter**: Handle all formats — "One turn deducted", "You have N turns this Stardate", "You have N turns left", "You don't have any turns left", "You recover N of your turns"
- **Transaction tracking**: Parse buy/sell haggling sequences for cargo tracking with cost basis (weighted average per unit)
- **Declined trades**: Correctly skip trades where the player can't afford (default `[0]`, no "Agreed" message)
- **Comma-formatted numbers**: Handle `Turns 1,000` in status bar

### New Features

- **`tw nearest-pair <sector>`**: Find nearest trade pairs sorted by hop distance from a given sector
- **HUD trade pair toggle**: Press `t` to switch between "Best Pairs" (by complementary count) and "Nearest Pairs" (by hops from current sector)
- **Turn warning colors**: Turns display goes yellow-inverse below 100, red below 50

### Fixes

- **Sync point ordering**: Multiple sync points (info blocks + status bars) processed in document order so the last one wins regardless of type
- **Transaction window**: Transactions only processed after the last sync point to prevent double-counting across full-file parses
