# Validation: PM — Code vs Feature Design & Use Cases

## Verdict: PASS

## Use Case Verification

| UC | Requirement | Implementation | Status |
|----|-------------|---------------|--------|
| 1 | Turns below threshold → RED ALERT overlay with fastest route to nearest safe sector | `HudDisplay._render` checks `status.turns_remaining < self._thresholds.alert`, calls `FindSafeHarbor.execute()` (BFS), renders centered overlay via `_render_alert_overlay` using `format_alert_overlay` content. Default threshold is 50. | ✓ |
| 2 | Already in safe sector → message instead of route | `FindSafeHarbor.execute()` checks if `from_sector in safe_ids` and returns `SafeHarborRoute` with `route=[from_sector]` (hops == 0). `format_alert_overlay` detects `route.hops == 0` and outputs "You are currently in a safe sector." with destination name. | ✓ |
| 3 | No known route → cheeky message | `FindSafeHarbor.execute()` returns `None` when BFS exhausts reachable graph without finding a safe sector. `format_alert_overlay` handles `None` with "Uhoh, I think you're in trouble." and "No known route to safe space." | ✓ |
| 4 | Persists below threshold, auto-clears above, no manual dismissal | `_render` conditionally renders overlay when `turns < alert`. When turns recover (`>= alert`), the `elif` branch clears cache (`self._safe_harbor_cache = None`). No keybinding or mechanism exists to dismiss the overlay. | ✓ |
| 5 | `tw safe-harbor` CLI command regardless of turn count | `CliAdapter.safe_harbor()` calls `find_safe_harbor.execute(status.sector_id)` unconditionally (no turn check). Registered as `safe-harbor` subcommand in `cli.py`. Handles all three states: route found, already safe, no route. Errors if no player status. | ✓ |
| 6 | Turn warning colors: yellow at 200, red at 100 | `_render_header` uses `self._thresholds.yellow` (200) and `self._thresholds.red` (100): `< alert` → red bold, `< red` → red bold, `< yellow` → yellow bold + reverse, else → yellow bold. | ✓ |
| 7 | Configurable thresholds in config.ini with defaults, per-profile override | `_DEFAULT_CONFIG` in `IniProfileStore` includes `turn_warning_yellow = 200`, `turn_warning_red = 100`, `turn_alert_threshold = 50` in `[DEFAULT]`. `resolve_config()` reads these via `get_config_value()` with `configparser`'s built-in section/DEFAULT cascade. Per-profile override works via standard INI section keys. `TurnThresholds` validates `yellow > red > alert`. | ✓ |

## Success Criteria Check

- [x] HUD displays a RED ALERT overlay when turns drop below the alert threshold (default 50) ← UC#1
- [x] The overlay shows the BFS shortest path from the current sector to the nearest safe sector ← UC#1
- [x] Safe sectors are defined as: Federation sectors (region == "The Federation") OR sectors containing StarDock (port_class == 0) ← UC#1
- [x] When already in a safe sector, the overlay shows "You are in a safe sector" instead of a route ← UC#2
- [x] When no path to safe space exists in the explored graph, the overlay shows a humorous failure message ← UC#3
- [x] The overlay persists while turns remain below the threshold and disappears when turns recover above it ← UC#4
- [x] No manual dismissal mechanism exists — the overlay is purely reactive to turn count ← UC#4
- [x] `tw safe-harbor` CLI command shows the nearest safe sector and route from the current position, regardless of turn count ← UC#5
- [x] Turn warning colors are: yellow at 200 turns, red at 100 turns ← UC#6
- [x] Turn warning thresholds (yellow, red, alert) are configurable in config.ini with defaults 200/100/50, overridable per-profile ← UC#7

## Detailed Findings

### UC#1 — RED ALERT Overlay with Route ✓

The overlay is rendered by `_render_alert_overlay` which:
- Centers the box horizontally and vertically (`(max_y - box_height) // 2`, `(max_x - box_width) // 2`)
- Draws a red bold border with `╔═╗║╚╝` characters
- Embeds "RED ALERT" in the top border
- Displays content from `format_alert_overlay`: turn count, destination sector, route with arrows, hop count

The BFS in `FindSafeHarbor.execute()` uses `get_safe_sector_ids()` which queries:
```sql
SELECT id FROM sectors WHERE region = 'The Federation'
UNION
SELECT sector_id FROM ports WHERE port_class = 0
```

This correctly identifies both Federation sectors and StarDock sectors as safe.

### UC#2 — Already Safe ✓

When `from_sector in safe_ids`, the use case returns immediately with `route=[from_sector]` (hops == 0). The overlay helper detects this and shows "You are currently in a safe sector." with the destination name (e.g., "The Federation" or "StarDock" or "The Federation / StarDock").

### UC#3 — No Route ✓

When BFS exhausts all reachable sectors without finding a safe one, `execute()` returns `None`. The overlay helper produces the exact cheeky message from the design: "Uhoh, I think you're in trouble." followed by "No known route to safe space."

### UC#4 — Persistence and Auto-Clear ✓

The `_render` method has a clear conditional structure:
- `if status.turns_remaining < self._thresholds.alert:` → render overlay (with sector-change caching)
- `elif self._safe_harbor_cache is not None:` → clear cache (overlay disappears)

No keybinding exists for dismissal. The only keybindings are `q` (quit) and `t` (toggle pairs). The overlay is purely reactive.

The sector-change caching (`_safe_harbor_sector != status.sector_id`) ensures the route recalculates when the player moves while the alert is active, matching the design's "route recalculates if sector changes while alert is active."

### UC#5 — CLI Command ✓

`CliAdapter.safe_harbor()` is implemented with all three output states:
- Route found: `"Safe harbor from sector {id}:"` with nearest sector, route (→ arrows), and hop count
- Already safe: `"You are currently in a safe sector ({name})."`
- No route: `"No known route to safe space from sector {id}."` with exploration hint

Error case: prints `"Error: No player position known. Play a session first."` to stderr and exits 1.

The command is registered in `cli.py` as `safe-harbor` (no arguments required).

### UC#6 — Turn Warning Colors ✓

The `_render_header` method implements the escalating color scheme:
- `< alert` (< 50): red bold (curses pair 4 + A_BOLD)
- `< red` (< 100): red bold (curses pair 4 + A_BOLD)
- `< yellow` (< 200): yellow bold + reverse (curses pair 3 + A_BOLD + A_REVERSE)
- else: yellow bold (curses pair 3 + A_BOLD)

This matches the design's turn warning table exactly.

### UC#7 — Configurable Thresholds ✓

The `_DEFAULT_CONFIG` in `IniProfileStore` includes all three threshold keys in `[DEFAULT]`:
```ini
turn_warning_yellow = 200
turn_warning_red = 100
turn_alert_threshold = 50
```

`resolve_config()` in `compose.py` reads these via `get_config_value(effective_name, key, default)` which uses `configparser`'s built-in fallback from profile section → `[DEFAULT]` → provided default. Per-profile override works by adding the key to a `[profile:name]` section.

`TurnThresholds` validates `yellow > red > alert` in `__post_init__`, preventing invalid configurations from propagating.

`hud.py` calls `resolve_config(args.profile)` and passes the resulting `thresholds` to `HudDisplay`. The CLI doesn't need thresholds (it uses `resolve_db_path` which wraps `resolve_config` and discards thresholds).

## Implementation Quality Notes

- **Deterministic BFS**: Uses standard BFS (deque, visited set) — guarantees shortest path (fewest hops) to nearest safe sector.
- **Caching**: Route is cached per sector (`_safe_harbor_sector`), only recalculated on sector change. No performance concern on 250ms refresh.
- **Overlay adapts to content**: Box width is `max(len(line) for line in lines) + 8`, capped at `max_x - 4`. Height adapts to number of content lines.
- **Route truncation**: Routes > 10 hops are truncated to first 8 sectors + "... (N more)" — prevents overlay from growing unbounded.
- **Safe sector naming**: `_build_name` combines "The Federation" and/or "StarDock" labels based on actual sector/port data, giving the player useful context about WHY the destination is safe.

## No Issues Found

All 7 use cases are satisfied by the implementation. All 10 success criteria are met. The feature is functionally complete.
