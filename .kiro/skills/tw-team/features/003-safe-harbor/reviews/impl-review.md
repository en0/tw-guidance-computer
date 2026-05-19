# Implementation Plan Review: Safe Harbor

**Reviewer**: Architect (Adversary Mode)
**Date**: 2025-05-17
**Verdict**: FAIL

## Critical Issues

### 1. Unit 7 — HUD Calls Use Case Directly from Render Method (Business Logic in Adapter)

The plan says `_render` checks `status.turns_remaining < thresholds.alert` and then calls `self._uc.find_safe_harbor.execute(status.sector_id)` inside the render method. This means the HUD adapter is making the decision about WHEN to trigger the safe harbor calculation — that's application-layer orchestration logic embedded in an adapter.

More critically, calling `find_safe_harbor.execute()` on every 250ms render tick while the alert is active means a full BFS runs 4 times per second. The plan acknowledges this in Risk Note #1 ("BFS completes in <1ms") but then says "cache the route and only recalculate on sector change" as a future optimization. The design explicitly says "route recalculates if sector changes while alert is active" — so caching IS required behavior, not an optimization.

**Problem**: The caching logic (track last sector, invalidate on change) is orchestration that belongs in the application layer or at minimum should be specified in the plan. The plan leaves this as a vague "if performance becomes an issue" note rather than specifying the required behavior.

**Fix**: Either:
- (a) Specify that `HudDisplay` caches the `SafeHarborRoute` result and only re-calls the use case when `status.sector_id` changes (same pattern as `_art_cache` / `_art_sector`), OR
- (b) Create a thin orchestration layer in the use case that accepts the previous sector and only recalculates when needed (over-engineering for this case)

Option (a) is correct — it matches the existing `_art_cache` pattern in the TUI. But the plan must SPECIFY this, not leave it as a risk note.

### 2. Unit 6 — `FindSafeHarbor` Calls `get_sector` and `get_port` for Label Resolution (Use Case Doing Too Much)

The plan says `FindSafeHarbor.execute()` does BFS to find the nearest safe sector, then calls `self._store.get_sector(destination)` for the region name and `self._store.get_port(destination)` to check if it's StarDock. This mixes two concerns:

1. Pathfinding (BFS to nearest safe sector)
2. Label resolution (determining the human-readable name for the destination)

The BFS already knows WHY a sector is safe — it terminates when it hits a sector in the `safe_sector_ids` set. But the plan's `get_safe_sector_ids()` returns a flat `list[int]` with no indication of whether each sector is Federation or StarDock.

**Problem**: After BFS finds the destination, the use case makes 2 additional store calls just to reconstruct information that was available (or derivable) at query time. This is inefficient and couples the use case to the store's sector/port retrieval methods for what is essentially a display concern.

**Fix**: Change `get_safe_sector_ids() -> list[int]` to return richer data. Options:
- (a) `get_safe_sectors() -> list[tuple[int, str]]` returning `(sector_id, label)` where label is "The Federation" or "StarDock" — but this violates the "ports speak domain types" rule (raw tuple).
- (b) Keep `get_safe_sector_ids() -> list[int]` but also have the use case build a lookup from the existing `get_sector` / `get_port` calls. The plan already does this — it's just 2 extra queries. This is acceptable for a use case that runs at most once per sector change.

On reflection, the current approach (2 extra queries after BFS) is acceptable given the caching requirement from Issue #1. The use case runs once per sector change, not 4x/second. **Downgrading to observation** — not blocking.

### 3. Unit 3 — `get_config_value` on `ProfileStore` is a Leaky Abstraction

The plan adds `get_config_value(profile_name: str, key: str, default: str) -> str` to the `ProfileStore` Protocol. This turns the profile store into a generic config reader — it's no longer just "profile management" but "arbitrary key-value config access."

**Problems**:
- The method signature exposes `configparser`'s `[DEFAULT]` cascade semantics through the port. A different adapter implementation (e.g., TOML, YAML, environment variables) would need to replicate this cascade behavior.
- The method returns `str` and the caller must parse to `int`. This pushes type conversion responsibility to the composition root, which is acceptable, but the port's contract doesn't document what keys are valid or what format the values should be in.
- The `ProfileStore` port currently has 5 methods, all about profiles. Adding a generic `get_config_value` breaks the cohesion of the abstraction.

**Fix**: Don't add `get_config_value` to the port. Instead, have the composition root read thresholds directly from the `IniProfileStore` instance (which it already constructs). The composition root already knows it's dealing with an INI file — it calls `IniProfileStore(config_path)` directly. Add a `get_threshold(profile_name: str, key: str, default: int) -> int` method on `IniProfileStore` as a concrete method (not on the Protocol). The composition root calls it directly, same as it calls `ensure_config_exists()` and `resolve_default_db_path()`.

Wait — looking at the existing code, `resolve_db_path()` in `compose.py` already constructs `IniProfileStore` directly and calls methods on it. The composition root doesn't go through the port for profile resolution. So adding threshold reading as a concrete method on `IniProfileStore` (not on the Protocol) is consistent with the existing pattern.

**Alternative fix**: If the architect insists on the port approach, at minimum rename it to something that communicates its purpose: `get_turn_threshold(profile_name: str, threshold: str, default: int) -> int` — typed, specific, documented. But this still pollutes the ProfileStore port with non-profile concerns.

### 4. Units 1 & 2 — Both in Same File Creates Parallel Conflict

The plan puts `SafeHarborRoute` and `TurnThresholds` in the same file (`domain/models/safe_harbor.py`) and lists them as separate units (1 and 2) in parallel group A. Two builders cannot work on the same file in parallel.

**Fix**: Either:
- (a) Merge Units 1 and 2 into a single unit (they're both small domain types in the same file), OR
- (b) Put them in separate files: `safe_harbor.py` and `turn_thresholds.py`

Option (a) is simpler and more honest — they're both tiny frozen dataclasses that will be written in 5 minutes.

### 5. Unit 9 — `resolve_turn_thresholds` Creates a Second `IniProfileStore` Instance

The plan says `hud.py` calls `resolve_turn_thresholds()` after `resolve_db_path()`. Looking at the existing code, `resolve_db_path()` already constructs an `IniProfileStore`, calls `ensure_config_exists()`, resolves the profile, and discards the store. If `resolve_turn_thresholds()` does the same thing, that's two separate `IniProfileStore` constructions reading the same file.

**Problem**: Wasteful and fragile. If the config file changes between the two calls (unlikely but possible), you get inconsistent state.

**Fix**: Refactor `resolve_db_path` to return both the db path AND the thresholds in a single call, or have the composition root construct `IniProfileStore` once and pass it to both resolution functions. The existing pattern in `compose.py` already constructs the store once in `resolve_db_path` — extend it to also extract thresholds.

Alternatively, create a `resolve_config(profile_name, config_path) -> ResolvedConfig` that returns a simple dataclass with `db_path: Path` and `thresholds: TurnThresholds`. This keeps the composition root clean.

## Minor Issues

### 6. `TurnThresholds` Default Values Don't Match Design's Turn Warning Table

The design specifies:
- ≥ 200: Yellow Bold
- 100–199: Yellow Bold + Reverse
- 50–99: Red Bold
- < 50: Red Bold + overlay

The plan's `TurnThresholds` has `yellow: int = 200`, `red: int = 100`, `alert: int = 50`. But the current HUD code uses `< 50` for red and `< 100` for yellow+reverse. The design says the NEW behavior is yellow at 200, yellow+reverse at 100-199, red at 50-99. The plan's thresholds map correctly to this.

However, the plan says Unit 7 updates `_render_header` to use `self._thresholds.yellow` and `self._thresholds.red` "instead of hardcoded 50/100." The current code uses `< 50` (red) and `< 100` (yellow+reverse). The new thresholds are `< 50` (alert/overlay), `< 100` (red), `< 200` (yellow+reverse). The plan doesn't specify the exact conditional logic — it just says "update turn warning color logic." This is ambiguous enough that a builder could get it wrong.

**Fix**: Specify the exact conditional chain:
```python
if turns < self._thresholds.alert:  # < 50: red bold (overlay handles the drama)
    attr = RED | BOLD
elif turns < self._thresholds.red:  # < 100: red bold
    attr = RED | BOLD
elif turns < self._thresholds.yellow:  # < 200: yellow bold + reverse
    attr = YELLOW | BOLD | REVERSE
else:
    attr = YELLOW | BOLD
```

### 7. `SafeHarborRoute.route` Uses `list[int]` — Mutable Default Concern

The plan specifies `route: list[int]` on a frozen dataclass. Per Domain-Value-Objects codespec Rule 5: "Use `field(default_factory=list)` for mutable default types." Since `route` has no default (it's required and validated as non-empty), this isn't technically a violation — but the plan should note that `route` has no default value to make this clear to the builder.

**Impact**: Non-blocking. The builder will see the validation requirement ("route non-empty") and not provide a default.

### 8. Plan Doesn't Specify `__init__.py` Re-export Updates

Unit 1 says "update `domain/models/__init__.py`" but Unit 2 doesn't mention it separately. Since they're in the same file this is fine, but the plan should be explicit that `SafeHarborRoute` AND `TurnThresholds` both get re-exported and added to `__all__`.

**Impact**: Non-blocking. Builder will follow the pattern.

### 9. `FindSafeHarbor` BFS Treats Graph as Undirected — Matches `FindPath` but May Be Wrong

Both `FindPath` and the planned `FindSafeHarbor` treat warps as bidirectional (`adj[w.from_sector].add(w.to_sector)` AND `adj[w.to_sector].add(w.from_sector)`). In TW2002, warps ARE bidirectional by default, but one-way warps exist. The existing codebase treats all warps as bidirectional — this is a pre-existing design choice, not a new issue.

**Impact**: Non-blocking. Consistent with existing behavior.

### 10. No Test for Overlay Rendering Behavior

Unit 7 says "Limited curses testing. Verify overlay logic via unit testing the use case." But the overlay has three distinct display states (route found, already safe, no route) with specific text content from the design. There's no way to verify the correct messages appear without SOME form of adapter testing.

**Fix**: At minimum, extract the overlay text generation into a testable helper (pure function that takes `SafeHarborRoute | None` + `turns_remaining` + `is_already_safe` and returns a list of strings). Then test the helper. The curses rendering of those strings doesn't need testing, but the content generation does.

## Codespec Compliance

| Spec | Status | Notes |
|------|--------|-------|
| Hexagonal Architecture | ⚠️ | Issue #1: orchestration logic (when to call use case, caching) unspecified in adapter |
| Use Case Pattern | ✅ | `@final`, `execute()`, constructor injection, returns domain type |
| Port Definitions | ⚠️ | Issue #3: `get_config_value` breaks ProfileStore cohesion |
| Domain Value Objects | ✅ | Frozen, validated, derived property |
| Domain Exception Hierarchy | ✅ | Uses existing `ValidationError` |
| Composition Root | ⚠️ | Issue #5: double construction of IniProfileStore |
| Testing Strategy | ⚠️ | Issue #10: no testable overlay content generation |
| Typing Discipline | ✅ | `@final` on use case, `@override` implied |
| Minimal Dependencies | ✅ | No new external deps |

## Design Coverage

| Use Case | Addressed | Unit |
|----------|-----------|------|
| UC#1: RED ALERT overlay with route | ✅ | Unit 7 |
| UC#2: Already safe message | ✅ | Unit 6 + 7 |
| UC#3: No route / cheeky message | ✅ | Unit 6 + 7 |
| UC#4: Auto-clear on turn recovery | ✅ | Unit 7 (conditional render) |
| UC#5: `tw safe-harbor` CLI | ✅ | Unit 8 |
| UC#6: Turn warning color adjustment | ✅ | Unit 7 |
| UC#7: Configurable thresholds | ✅ | Units 2, 5, 9 |

All use cases from the design are addressed.

## Summary

The plan's overall architecture is sound — the layer separation is correct, the BFS approach is consistent with existing use cases, and all design use cases are covered. However, there are structural issues that will cause problems during build:

1. The HUD caching requirement is specified as a "maybe later" optimization when it's actually required behavior
2. The `get_config_value` port method breaks ProfileStore's cohesion
3. Parallel group A has a file conflict (Units 1 & 2 share a file)
4. Double IniProfileStore construction is wasteful
5. Overlay content generation isn't testable as specified

## Required Changes for PASS

1. **Specify HUD caching explicitly in Unit 7**: Add `_safe_harbor_cache: SafeHarborRoute | None` and `_safe_harbor_sector: int | None` fields. Only call `find_safe_harbor.execute()` when sector changes. Same pattern as `_art_cache`.

2. **Remove `get_config_value` from the `ProfileStore` Protocol**: Read thresholds via a concrete method on `IniProfileStore` called directly from the composition root (consistent with existing `resolve_db_path` pattern which already uses `IniProfileStore` directly).

3. **Merge Units 1 and 2 into a single unit**: They share a file. One builder, one unit.

4. **Consolidate config reading in composition root**: Either extend `resolve_db_path` to also return thresholds, or create a single `resolve_config()` function that constructs `IniProfileStore` once and extracts both db_path and thresholds.

5. **Extract overlay content generation into a testable helper**: A pure function that produces the overlay text lines, testable without curses.

---

# Second-Pass Adversarial Review

**Reviewer**: Architect (Adversary Mode)
**Date**: 2025-05-17
**Verdict**: PASS

## Verification of Required Changes

### 1. HUD caching specified explicitly — ✅ FIXED

The Architecture Decisions section explicitly states the caching pattern: `_safe_harbor_cache: SafeHarborRoute | None` and `_safe_harbor_sector: int | None`. Unit 7 specifies:
- Fields added to `__init__`
- Sector-change check: `if self._safe_harbor_sector != status.sector_id` before calling the use case
- Cache cleared when turns recover above threshold

This matches the existing `_art_cache` / `_art_sector` pattern in `tui.py`. No ambiguity for the builder.

### 2. `get_config_value` removed from `ProfileStore` Protocol — ✅ FIXED

Architecture Decisions section: "Add a concrete `get_config_value(...)` method on `IniProfileStore` (NOT on the `ProfileStore` Protocol)."

Unit 4 reinforces: "Add a concrete method (NOT on the Protocol)."

The `ProfileStore` Protocol remains cohesive — only profile management methods. The composition root calls `get_config_value` directly on the `IniProfileStore` instance, consistent with how `resolve_db_path()` already uses `IniProfileStore` directly without going through the Protocol.

### 3. Units 1 and 2 merged — ✅ FIXED

The revised plan has a single Unit 1 covering both `SafeHarborRoute` and `TurnThresholds` in `domain/models/safe_harbor.py`. No parallel file conflict. Both types are re-exported from `__init__.py` and added to `__all__`.

### 4. Config reading consolidated — ✅ FIXED

Unit 9 specifies `resolve_config()` that constructs `IniProfileStore` once and extracts both `db_path` and `TurnThresholds`. `resolve_db_path()` becomes a thin wrapper: `return resolve_config(profile_name, config_path)[0]`. No double construction. Backward compatibility preserved for CLI.

### 5. Overlay content generation extracted into testable pure function — ✅ FIXED

Unit 6 defines `format_alert_overlay(route: SafeHarborRoute | None, turns_remaining: int, current_sector: int) -> list[str]` as a pure function in `adapters/inbound/alert_overlay.py`. Handles all three cases (route found, already safe, no route). Has its own test file. Unit 7 calls this helper and only handles curses rendering of the returned strings.

## New Issues Check

### Observation 1: `format_alert_overlay` placement in adapters/inbound

Unit 6 places the pure function in `adapters/inbound/alert_overlay.py`. This is acceptable — it's a helper for the inbound TUI adapter. It has no I/O, no external dependencies, and only imports the `SafeHarborRoute` domain type. The alternative (application layer) would be over-engineering for what is essentially a display formatting helper. The placement is consistent with keeping display logic near the adapter that uses it.

**Impact**: Non-blocking. Acceptable placement.

### Observation 2: Unit 7 turn warning conditional has redundant branch

The specified conditional:
```python
if turns < self._thresholds.alert:    # < 50: red bold
    attr = RED | BOLD
elif turns < self._thresholds.red:    # < 100: red bold
    attr = RED | BOLD
elif turns < self._thresholds.yellow: # < 200: yellow bold + reverse
    attr = YELLOW | BOLD | REVERSE
else:
    attr = YELLOW | BOLD
```

The first two branches produce identical output (`RED | BOLD`). This is technically correct (the overlay handles the visual drama for < alert, so the status bar just stays red), but a builder might simplify to `if turns < self._thresholds.red` for both. The design says < 50 is "Red Bold (+ overlay appears)" and 50-99 is "Red Bold" — same color, different overlay behavior. The conditional is correct as specified because the overlay logic is separate from the color logic.

**Impact**: Non-blocking. Correct as specified. A builder could collapse the first two branches into `if turns < self._thresholds.red` without behavioral change, but the explicit form documents intent.

### Observation 3: `resolve_config` return type

Unit 9 shows `resolve_config()` returning `tuple[Path, TurnThresholds]`. This is a composition root helper, not a domain boundary — raw tuples are acceptable here (Composition Root codespec doesn't require domain types for internal wiring helpers). The function is private to the composition module.

**Impact**: Non-blocking. Acceptable.

### Observation 4: Unit 5 BFS terminates at first safe sector — correct

`FindSafeHarbor` uses BFS (same as `FindPath`) but terminates at the FIRST safe sector reached rather than a specific target. This is the correct algorithm for "nearest safe sector." The plan correctly specifies this termination condition. Consistent with the existing `FindPath` pattern (undirected graph, `get_all_warps()`).

**Impact**: Non-blocking. Correct.

### Observation 5: `FindSafeHarbor` not in `UseCases` container until Unit 9

Units 7 and 8 depend on `FindSafeHarbor` being in the `UseCases` container, but Unit 9 is where it gets added. The parallel groups handle this correctly — Group C (Units 7, 8) runs after Group B (which includes Unit 5), and Group D (Unit 9) runs after Group C. However, Units 7 and 8 reference `self._uc.find_safe_harbor` which won't exist on the `UseCases` dataclass until Unit 9 adds the field.

This means builders for Units 7 and 8 need to know the field name in advance. The plan specifies it clearly in Unit 9: `find_safe_harbor: FindSafeHarbor`. Builders can code against this contract. The type checker will catch any mismatch when Unit 9 lands.

**Impact**: Non-blocking. Standard practice for parallel development against a known interface.

## Codespec Compliance (Revised)

| Spec | Status | Notes |
|------|--------|-------|
| Hexagonal Architecture | ✅ | Caching in adapter matches existing pattern; orchestration stays in use case |
| Use Case Pattern | ✅ | `@final`, `execute()`, constructor injection, returns domain type |
| Port Definitions | ✅ | `get_config_value` is concrete on adapter, not on Protocol |
| Domain Value Objects | ✅ | Frozen, validated, derived property, no mutable defaults |
| Domain Exception Hierarchy | ✅ | Uses existing `ValidationError` |
| Composition Root | ✅ | Single `IniProfileStore` construction via `resolve_config()` |
| Testing Strategy | ✅ | Overlay content testable via pure function; domain types tested |
| Typing Discipline | ✅ | `@final` on use case, `@override` on adapter methods |
| Minimal Dependencies | ✅ | No new external deps |

## Design Coverage (Unchanged)

All 7 use cases from the design are addressed by the plan. No gaps.

## Summary

All 5 required changes from the first-pass review have been addressed correctly. The revised plan:
- Specifies HUD caching explicitly with the same pattern as `_art_cache`
- Keeps `get_config_value` off the Protocol (concrete method only)
- Merges the domain types into a single unit
- Consolidates config reading into one `IniProfileStore` construction
- Extracts overlay content into a testable pure function

No new blocking issues introduced. The plan is ready for build.
