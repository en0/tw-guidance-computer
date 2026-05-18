# Changelog

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
