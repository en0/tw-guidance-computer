# Changelog

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
