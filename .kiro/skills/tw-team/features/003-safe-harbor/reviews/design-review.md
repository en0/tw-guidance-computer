# Design Review — PM Adversary

## Verdict: PASS (with notes)

## Use Case Fidelity

All 7 user use cases are present verbatim in the "Use Cases" section. None dropped, merged, or reinterpreted. ✓

## Use Case Coverage

| UC | Requirement | Design Coverage | Status |
|----|-------------|----------------|--------|
| 1 | Turns below threshold → RED ALERT overlay with fastest route to nearest safe sector | Overlay mockup shown, BFS shortest path, safe = Federation OR StarDock (port_class == 0) | ✓ |
| 2 | Already in safe sector → message instead of route | Separate overlay variant shown: "You are currently in a safe sector." | ✓ |
| 3 | No known route → cheeky message | Overlay variant: "Uhoh, I think you're in trouble." | ✓ |
| 4 | Alert persists while below threshold, auto-clears when above, no manual dismissal | Explicitly stated: appears on first tick below, disappears on first tick above, no dismissal mechanism | ✓ |
| 5 | `tw safe-harbor` CLI command regardless of turn count | CLI section with output examples for all three states (route, already safe, no route) | ✓ |
| 6 | Turn warning colors adjust: yellow at 200, red at 100 | Turn Warning Colors table specifies new thresholds | ✓ |
| 7 | Thresholds configurable in config file with defaults, overridable per-profile | Configuration section shows INI keys in `[DEFAULT]` with per-profile override example | ✓ |

## Issues Found

### Issue 1: No existing store method to query sectors by region — "New Queries Needed" is underspecified (MEDIUM)

The design says under "New Queries Needed":
> A way to find all "safe" sector IDs: sectors where `region == "The Federation"` OR sectors containing a port with `port_class == 0`. This is a new query on existing data.

This is correct — the data IS stored. However, the `GameStateStore` Protocol currently has NO method to retrieve sectors by region. There is no `get_all_sectors()`, no `get_sectors_by_region()`, nothing. The only sector query is `get_sector(sector_id: int) -> Sector | None` which requires knowing the sector ID already.

The design correctly identifies this as a "new query" but categorizes it under "Already Available" data. The DATA is available (sectors have regions stored in SQLite), but the QUERY PATH does not exist. This means the implementation will need to:
1. Add a new method to the `GameStateStore` Protocol (port change)
2. Implement it in `SqliteGameStateStore` (adapter change)

This is not a blocker — it's straightforward work — but the design should be clearer that this requires a port extension, not just a new SQL query. The architect will figure it out, but the design implies it's simpler than it is.

**Impact**: Medium. Won't block implementation but could cause underestimation of scope.

### Issue 2: FindPath BFS treats warps as bidirectional — design doesn't address directionality (LOW)

The existing `FindPath` use case builds an undirected graph (`adj[w.from_sector].add(w.to_sector)` AND `adj[w.to_sector].add(w.from_sector)`). In TW2002, warps are NOT always bidirectional — one-way warps exist (though they're uncommon in Federation space).

The design says "BFS shortest path" but doesn't specify whether the safe harbor route should use directed or undirected traversal. If the existing `FindPath` behavior (undirected) is reused, the route might suggest a path that's not actually traversable in the required direction.

**Impact**: Low. One-way warps are rare, and the existing `FindPath` already makes this assumption. The safe harbor feature inherits the same limitation. Not a design flaw per se — it's a pre-existing system behavior. But worth noting for the architect.

### Issue 3: Turn warning color table introduces a NEW threshold band not in any UC (INFORMATIONAL)

The design specifies four bands:
- ≥ 200: Yellow Bold
- 100–199: Yellow Bold + Reverse
- 50–99: Red Bold
- < 50: Red Bold + overlay

UC#6 says "yellow at 200 turns, red at 100 turns." The design interprets this as TWO yellow bands (≥200 normal, 100-199 reverse) and TWO red bands (50-99 bold, <50 bold + overlay). The "Yellow Bold + Reverse" at 100-199 is a design embellishment — the user said "yellow at 200, red at 100" which more naturally reads as: yellow from 200 down to 100, red below 100.

The current implementation (confirmed in `tui.py`) has:
- < 50: red bold
- < 100: yellow bold + reverse
- else: yellow bold

The design changes this to:
- < 50: red bold (+ overlay)
- 50-99: red bold
- 100-199: yellow bold + reverse
- ≥ 200: yellow bold (presumably this means turns ≥ 200 get no special treatment? Or always yellow?)

Wait — the current code shows yellow bold as the default (no threshold check for "above 100"). The design's table says "≥ 200" gets yellow bold, implying turns above 200 are yellow. But what about turns above some higher number? The user's UC#6 says "yellow at 200 turns" — meaning the yellow warning STARTS at 200. Above 200, presumably no warning color at all (normal display).

The design doesn't specify what happens above 200. Is the turn count always yellow? Or only yellow once it drops below 200? The current implementation appears to always show turns in yellow bold (it's the else branch). The design's table implies yellow starts at 200, but doesn't explicitly state "no color above 200."

**Impact**: Informational. The intent is clear enough for the builder. The current code already uses yellow as the base color for turns, so "yellow at 200" likely means "yellow is the starting warning color, escalating from there."

### Issue 4: Config reading mechanism doesn't exist yet in ProfileStore (LOW)

UC#7 requires reading `turn_warning_yellow`, `turn_warning_red`, and `turn_alert_threshold` from the config file. The current `ProfileStore` Protocol and `IniProfileStore` implementation have NO generic "get config value" method. They only read `db` and `default_profile`.

The design correctly identifies Feature 002 as a dependency and says thresholds are stored in `config.ini`. But Feature 002's `ProfileStore` was designed to manage profiles, not to be a general config reader. Reading arbitrary keys from profile sections will require either:
1. Extending `ProfileStore` with a `get_config_value(profile_name, key, default)` method
2. Extending `Profile` to carry additional fields
3. Having the composition root read the INI file directly (bypassing the port)

This is an implementation detail the architect will resolve, but the design should acknowledge that the config reading infrastructure for arbitrary keys doesn't exist yet — Feature 002 only built profile CRUD, not general config access.

**Impact**: Low. The `configparser` data is there (keys in profile sections cascade from `[DEFAULT]`), but the code path to read them doesn't exist. Straightforward to add.

### Issue 5: "Fastest route" vs "shortest path" ambiguity (INFORMATIONAL)

UC#1 says "fastest route to the nearest safe sector." The design says "BFS shortest path." In an unweighted graph, BFS gives the shortest path (fewest hops), which IS the fastest route (each hop = 1 turn). So these are equivalent. Just noting the terminology alignment is correct — no issue here.

### Issue 6: Overlay "maximum height cap" is unspecified (LOW)

The design says "Overlay dimensions adapt slightly to route length (more hops = taller box), with a maximum height cap." But doesn't specify what the cap is. If the route is 20 hops, does the overlay show all 20 sectors? Truncate? Show "... (17 more hops)"?

**Impact**: Low. The builder/UI designer will need to make a judgment call. For a 50×10 overlay, a route of more than ~8-10 hops won't fit on one line. The design should specify truncation behavior.

## Success Criteria Testability

| Criterion | Testable? | How |
|-----------|-----------|-----|
| RED ALERT overlay at threshold | ✓ | Set turns < 50, verify overlay renders |
| BFS shortest path shown | ✓ | Known graph, verify route matches expected BFS |
| Safe = Federation OR port_class 0 | ✓ | Create sectors with each condition, verify detection |
| Already safe → message | ✓ | Set player in Federation sector, verify message variant |
| No route → humorous message | ✓ | Isolated sector with no path to safe space, verify message |
| Persists below / clears above | ✓ | Toggle turns across threshold, verify overlay state |
| No manual dismissal | ✓ | Verify no keybinding or mechanism exists |
| CLI command works | ✓ | Run `tw safe-harbor`, verify output |
| Yellow at 200, red at 100 | ✓ | Check color attributes at various turn counts |
| Configurable thresholds | ✓ | Set custom values in config, verify behavior changes |

All criteria are measurable and testable. ✓

## Data Availability

| Data | Available? | Source |
|------|-----------|--------|
| Player turns remaining | ✓ | `PlayerStatus.turns_remaining` |
| Current sector ID | ✓ | `PlayerStatus.sector_id` |
| Sector region | ✓ | `Sector.region` field (stored in SQLite) |
| StarDock detection | ✓ | `Port.port_class == 0` via `get_port()` or `get_all_ports()` |
| Warp graph | ✓ | `get_all_warps()` |
| BFS pathfinding | ✓ | `FindPath` use case exists |
| Query sectors by region | ⚠️ | Data exists but no query method on the port (see Issue 1) |
| Config thresholds | ⚠️ | INI infrastructure exists but no generic read method (see Issue 4) |

## Scope Check

No scope creep detected. The design explicitly defers:
- Dynamic thresholds based on distance
- Threat tracking
- Manual dismissal
- Audio alerts
- Animated effects
- Planet/corporate territory as "safe"
- Configuring what counts as "safe"

The turn warning color changes (UC#6) are a modification of existing behavior, not new scope. The configuration (UC#7) leverages existing Feature 002 infrastructure.

## Dependency Risk

The design depends on Feature 002 (Profile-Based Configuration) being complete. Feature 002's status is "building" — if it's not merged before this feature starts implementation, the config reading for thresholds will be blocked. The design correctly identifies this dependency.

## Summary

The design is faithful to all 7 use cases, well-scoped, and the data requirements are largely satisfied by existing infrastructure. The two medium/low gaps (no store method for querying sectors by region, no generic config value reader) are implementation details that the architect will resolve — they don't represent missing data or impossible requirements. The overlay behavior is well-specified across all three states. Success criteria are testable and traceable to use cases.
