# Feature Design: Safe Harbor

STATUS: complete

## Use Cases (from user — do not modify)
1. When my turns drop below a threshold (default 50), the HUD shows a RED ALERT style overlay centered on screen, covering both the data and art areas, with the fastest route to the nearest safe sector.
2. If I'm already in a safe sector when the alert triggers, it shows a message telling me I'm currently in a safe sector instead of a route.
3. If no known route to safe space exists in the explored graph, it shows a cheeky message like "Uhoh, I think you're in trouble."
4. The alert persists while turns remain below the threshold and auto-clears when turns recover above it. No manual dismissal — the HUD is informational, not a control panel.
5. I can run `tw safe-harbor` from the CLI to check the nearest safe sector and route on demand, regardless of turn count.
6. The existing turn warning colors adjust: yellow at 200 turns, red at 100 turns (the safe harbor alert fires at 50).
7. Turn warning thresholds (yellow, red, alert) are configurable in the config file with sensible defaults (200/100/50), overridable per-profile for power users.

## Problem
Players get absorbed in trading runs and lose track of their remaining turns. When turns drop critically low, they may be stranded in hostile or uncharted space with no time to reach safety. The game doesn't warn you until it's too late — you simply run out of turns and your ship is left vulnerable. A dramatic visual alert with an escape route gives the player a fighting chance to reach Federation space or StarDock before their turns expire.

## Success Criteria
- [ ] HUD displays a RED ALERT overlay when turns drop below the alert threshold (default 50) ← UC#1
- [ ] The overlay shows the BFS shortest path from the current sector to the nearest safe sector ← UC#1
- [ ] Safe sectors are defined as: Federation sectors (region == "The Federation") OR sectors containing StarDock (port_class == 0) ← UC#1
- [ ] When already in a safe sector, the overlay shows "You are in a safe sector" instead of a route ← UC#2
- [ ] When no path to safe space exists in the explored graph, the overlay shows a humorous failure message ← UC#3
- [ ] The overlay persists while turns remain below the threshold and disappears when turns recover above it ← UC#4
- [ ] No manual dismissal mechanism exists — the overlay is purely reactive to turn count ← UC#4
- [ ] `tw safe-harbor` CLI command shows the nearest safe sector and route from the current position, regardless of turn count ← UC#5
- [ ] Turn warning colors are: yellow at 200 turns, red at 100 turns ← UC#6
- [ ] Turn warning thresholds (yellow, red, alert) are configurable in config.ini with defaults 200/100/50, overridable per-profile ← UC#7

## User-Facing Behavior

### HUD Overlay — RED ALERT

When the player's turns drop below the alert threshold, a centered overlay appears on the HUD, covering portions of both the two-column data area and the art panel. The overlay has a Star Trek II "Red Alert" aesthetic — red border, urgent messaging, high contrast.

**Overlay layout (approximately 50×10 characters, centered):**

```
╔══════════════ RED ALERT ══════════════╗
║                                       ║
║   TURNS CRITICAL: 37 remaining        ║
║                                       ║
║   Nearest safe harbor: Sector 1       ║
║   Route: 616 → 544 → 301 → 1         ║
║   Distance: 3 hops                    ║
║                                       ║
╚═══════════════════════════════════════╝
```

**When already safe (UC#2):**

```
╔══════════════ RED ALERT ══════════════╗
║                                       ║
║   TURNS CRITICAL: 42 remaining        ║
║                                       ║
║   You are currently in a safe sector. ║
║   (The Federation)                    ║
║                                       ║
╚═══════════════════════════════════════╝
```

**When no route exists (UC#3):**

```
╔══════════════ RED ALERT ══════════════╗
║                                       ║
║   TURNS CRITICAL: 12 remaining        ║
║                                       ║
║   Uhoh, I think you're in trouble.    ║
║   No known route to safe space.       ║
║                                       ║
╚═══════════════════════════════════════╝
```

**Visual style:**
- Border: bright red (`╔ ═ ╗ ║ ╚ ╝`) with bold attribute
- "RED ALERT" header: bright red, bold, centered in top border
- Turn count: white/bright on red background (high contrast)
- Route sectors: cyan (matches existing sector display color)
- Background of overlay: black (overwrites whatever is beneath)

**Behavior:**
- Appears on the first HUD refresh tick where `turns_remaining < alert_threshold`
- Redraws every 250ms tick (same as all HUD content) — route recalculates if sector changes while alert is active
- Disappears on the first tick where `turns_remaining >= alert_threshold`
- Centered horizontally and vertically within the terminal
- Overlay dimensions adapt slightly to route length (more hops = taller box), with a maximum height cap

### Turn Warning Colors (UC#6)

The status bar turn display uses escalating colors:

| Turns Remaining | Color | Attribute |
|----------------|-------|-----------|
| ≥ 200 | Yellow | Bold |
| 100–199 | Yellow | Bold + Reverse (flashing attention) |
| 50–99 | Red | Bold |
| < 50 | Red | Bold (+ overlay appears) |

This replaces the current thresholds (yellow at 100, red at 50).

### CLI Command: `tw safe-harbor`

Shows the nearest safe sector and route from the player's current position, regardless of turn count. Useful for planning ahead.

```
$ tw safe-harbor
Safe harbor from sector 616:
  Nearest: Sector 1 (The Federation, StarDock)
  Route: 616 → 544 → 301 → 1 (3 hops)
```

When already safe:
```
$ tw safe-harbor
You are currently in a safe sector (The Federation).
```

When no route:
```
$ tw safe-harbor
No known route to safe space from sector 616.
Explore more sectors to find a path to The Federation or StarDock.
```

Errors if no player status in DB: `Error: No player position known. Play a session first.`

### Configuration (UC#7)

Thresholds stored in `config.ini`:

```ini
[DEFAULT]
turn_warning_yellow = 200
turn_warning_red = 100
turn_alert_threshold = 50
```

Per-profile override:
```ini
[profile:practice]
db = ~/.local/share/tw-guidance-computer/practice.db
turn_alert_threshold = 30
```

Keys cascade from `[DEFAULT]` to all profiles (standard `configparser` behavior). A player on a fast-paced server can lower the alert threshold; a cautious player can raise it.

## Data Requirements

### Already Available
- **Player turns remaining**: Tracked in `PlayerStatus` (from status bar and sync points)
- **Current sector ID**: Tracked in `PlayerStatus`
- **Sector regions**: Stored in `Sector.region` field (parsed from sector display: "616 in The Federation.")
- **StarDock detection**: Port with `port_class == 0` (already stored in `Port` model)
- **Warp graph**: All warp connections stored, `get_all_warps()` available
- **BFS pathfinding**: `FindPath` use case exists with full BFS implementation

### New Data Needed
- **None from the game session.** All required data is already parsed and stored.

### New Queries Needed
- A way to find all "safe" sector IDs: sectors where `region == "The Federation"` OR sectors containing a port with `port_class == 0`. This is a new query on existing data.

### Storage
- No new tables or columns needed.
- Turn warning thresholds stored in config.ini (feature 002 infrastructure), not in the database.

## Dependencies
- **Feature 002 (Profile-Based Configuration)**: Required for storing configurable thresholds in `config.ini`. Without feature 002, thresholds would need to be hardcoded or passed as CLI flags. The config infrastructure (reading keys from profile sections with `[DEFAULT]` cascade) must be available.
- **Existing BFS pathfinding**: `FindPath` use case or equivalent BFS logic for route calculation.
- **Existing sector/port data**: The store must have Federation sectors and StarDock ports discoverable. This depends on the player having explored enough of the map — the feature gracefully handles the "no route" case.

## Out of Scope
- Dynamic threshold based on distance to safe space (e.g., "alert when turns < hops to safety + buffer") — explicitly rejected in favor of a simple static threshold
- Threat tracking or hostile player awareness — that's a separate future feature
- Route planning or navigation assistance beyond the safe harbor alert
- Manual dismissal, snooze, or acknowledgment of the alert
- Audio alerts or terminal bell
- Animated overlay effects (flashing, scrolling)
- Safe harbor based on planet ownership or corporate territory — only Federation and StarDock count
- Configuring what counts as "safe" (always Federation + StarDock)

## Open Questions
None — all resolved during discussion.

## TW Expert Notes
- **Federation space**: Sectors with region "The Federation" are safe — no combat allowed, no theft. This is the canonical safe zone in TW2002.
- **StarDock**: Always a Class 0 / "Special" port. Located in any sector (server-configurable, not fixed to sector 1). StarDock sectors are safe because StarDock provides all services and is a natural resting point.
- **Turn recovery**: Turns recover via the `T` command at StarDock (costs credits) or by waiting for the daily turn reset. The alert auto-clears when turns recover above the threshold — this handles both recovery methods correctly.
- **Federation detection**: The parser already captures region names from sector displays (`Sector : 616 in The Federation.`). The string match is exact: `"The Federation"`. Other regions like "The Frontier" or "uncharted space" are NOT safe.
