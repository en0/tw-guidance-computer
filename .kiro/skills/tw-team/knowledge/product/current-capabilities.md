# Current Capabilities

What the system can do today (v0.2.0).

## Parsing

The parser extracts the following from raw TW2002 session logs:

### Sector Discovery
- Sector ID and region name from sector displays
- Explored vs. unexplored status
- Warp connections (directional graph edges)
- Unexplored warp targets marked as such

### Port Discovery
- Port name, class, and type code from sector displays
- Type code: 3-char string (S=selling, B=buying) for Fuel/Org/Equ
- Commerce report parsing: detailed quantity and percentage data per commodity

### Player State Tracking
- Current sector (from command prompts and sector displays)
- Turns remaining (set, zero, recover events)
- Credits
- Cargo with cost basis (weighted average on buy)
- Total/empty holds count
- Sync points: `<Info>` blocks and compact status bars reset state authoritatively

### Transaction Tracking
- Buy/sell detection from haggling sequences
- Quantity from "Agreed, N units"
- Price extraction from haggling (last price before acceptance)
- Cost basis: weighted average when buying more of same commodity
- Cargo removal on sell

### Chat Capture
- Sub-space radio messages
- Fed comm-link messages
- Sender and message text extracted

## Use Cases (Application Layer)

| Use Case | What It Does |
|----------|-------------|
| ParseLogChunk | Core parser — processes text, updates store |
| FindTradePairs | Finds adjacent ports with complementary buy/sell patterns |
| FindNearestPair | BFS from player position to find closest trade pairs |
| FindPath | BFS shortest path between two sectors |
| FindSellLocations | BFS to find nearest ports buying player's cargo |
| FindNearbyPorts | BFS to find all ports within N hops |
| SearchPorts | Pattern match on port type codes (wildcard support) |

## Interfaces

### HUD (tw-hud)
- Real-time curses TUI
- Two-panel layout: cargo/sell-advice left, pairs/comms right
- 250ms refresh, non-blocking input
- Keybindings: q (quit), t (toggle pairs mode)
- Turn warnings with color escalation

### CLI (tw)
- 10 subcommands for querying the knowledge base
- status, sector, ports, pairs, path, search, nearby, nearest-pair, sell, chat
- Reads same SQLite DB the HUD writes to

## Data Persistence

- SQLite with WAL mode
- Accumulates across sessions — knowledge never lost
- Concurrent read/write safe (HUD writes, CLI reads)
- Location: `~/.local/share/tw-guidance-computer/game.db`

## What It Cannot Do (Known Gaps)

- No threat tracking (player sightings, hostile alerts)
- No sector activity log (warp-in/out events)
- No actual haggling price capture for cost basis (uses 0.0 from sync points)
- No chat parsing for all message types (only radio + fed)
- No dead-end detection
- No graph visualization
- No watch mode / incremental re-parse on file change
- No colonist tracking in cargo display (parsed but not shown in HUD)

See `docs/future-ideas.md` for the full wishlist.
