# Implementation Plan: Parser Reset

## Overview

Rewrite the parser to 5 patterns + status bar resync, add self-healing warps (delete+insert), change intel import warp strategy to replace-per-sector-if-newer, and stub out cargo (always empty). This is a simplification — removing commerce reports, transactions, haggling, chat, and cargo tracking.

## Work Units

### Unit 1: Add `replace_warps_from_sector` to GameStateWriter port

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/ports/game_state_writer.py`
- **Description**: Add a new method `replace_warps_from_sector(sector_id: int, warps: list[WarpConnection]) -> None` to the `GameStateWriter` Protocol. This method deletes all existing warps where `from_sector = sector_id` and inserts the provided set. Docstring documents the self-healing semantics.
- **Dependencies**: None.
- **Tests**: No direct tests — Protocol methods are tested via their adapter implementation (Unit 3).

### Unit 2: Rewrite ParseLogChunk

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/parse_log_chunk.py`
- **Description**: Clean rewrite of the parser. The new parser has exactly 5 patterns + status bar resync:
  1. **Command prompt** — `\[(\d+)\]\s*\(\?=Help\)` → sets current sector
  2. **Sector display block** — `Sector\s+:\s+(\d+)\s+in\s+(.+?)\.` NOT preceded by `(T)`, `(S)`, `(*)`, `(\d)` markers → sets current sector, upserts sector, extracts ports/planets from lines between Sector and Warps, then calls `replace_warps_from_sector` with the complete warp set
  3. **Turns** — `You have (\d+) turns this Stardate` and `One turn deducted, (\d+) turns left` → sets turns
  4. **Credits** — `You have ([0-9,]+) credits` and `You have ([0-9,]+) credits and (\d+) empty cargo holds` → sets credits (bank pattern ignored)
  5. **Status bar** — `Sect\s+(\d+)│Turns\s+([0-9,]+)│Creds\s+([0-9,]+)` → force-resync sector, turns, credits

  Nav menu exclusion: Before matching sector display, check if the line is preceded by `^\s*\([TS*\d]\)` on the same line. If so, skip. Also track a "nav menu active" flag: when a nav-prefixed sector line is seen, suppress port/planet parsing until the next non-indented, non-nav-prefixed sector line or command prompt.

  Removed: commerce reports, `<Info>` block parsing, transaction tracking, chat extraction, cargo state, `_SyncPoint` dataclass, `CargoManifest` usage.

  The parser still calls `set_player_status` with `cargo=[]` always. Holds fields set to 0.

  State retained across calls: `_current_sector`, `_turns_remaining`, `_credits` (minimal).

- **Dependencies**: Unit 1 (needs `replace_warps_from_sector` on the port).
- **Tests**: Complete rewrite of `tests/test_application/test_parse_log_chunk.py`. Test classes:
  - `TestCommandPrompt` — sector extraction from prompt
  - `TestSectorDisplay` — sector, port, planet, warp extraction from display block
  - `TestSelfHealingWarps` — verifies `replace_warps_from_sector` called (not `upsert_warp`)
  - `TestNavMenuExclusion` — nav menu lines with (T)/(S)/(*)/(N) prefixes don't trigger parsing; indented Ports/Planets under nav entries also excluded
  - `TestTurns` — both turn patterns
  - `TestCredits` — both credit patterns, bank ignored
  - `TestStatusBar` — force-resync of sector/turns/credits
  - `TestCargoStubbed` — cargo always empty in player status

### Unit 3: Implement `replace_warps_from_sector` in SqliteGameStateStore

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/sqlite_store.py`
- **Description**: Add `replace_warps_from_sector` method: `DELETE FROM warps WHERE from_sector = ?` then `INSERT INTO warps` for each warp in the list. Single transaction (no intermediate commits). Sets `updated_at = time.time()` and `source = NULL` (local observation). Uses `@override` decorator.
- **Dependencies**: Unit 1 (port definition).
- **Tests**: `tests/test_adapters/test_sqlite_store.py` — new test class `TestReplaceWarpsFromSector`:
  - Replaces existing warps from a sector
  - Inserts when no prior warps exist
  - Doesn't affect warps from other sectors
  - Removes warps with non-NULL source (intel-imported) when visiting sector

### Unit 4: Change intel import warp strategy to replace-per-sector-if-newer

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/sqlite_store.py`, `src/tw_guidance_computer/application/ports/intel_store.py`
- **Description**: Change `import_warps` from INSERT OR IGNORE (additive) to replace-per-sector-if-newer:
  1. Group incoming warps by `from_sector`
  2. For each sector group: get max `updated_at` of local warps from that sector
  3. If imported timestamp > local max: DELETE all warps from that sector, INSERT the imported set (with source and updated_at)
  4. If local is newer or equal: skip that sector's warps

  Update the `IntelStore` Protocol docstring for `import_warps` to document the new strategy.

- **Dependencies**: None (independent of parser rewrite).
- **Tests**: Update `tests/test_adapters/test_sqlite_intel.py` — modify existing `import_warps` tests:
  - Newer import replaces all warps from a sector
  - Older import is skipped
  - Mixed sectors: some replaced, some skipped
  - New sector (no local warps) always imported

### Unit 5: Stub cargo at adapter level

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/sqlite_store.py`
- **Description**: Modify `get_player_status` to always return `cargo=[]` regardless of what's stored in `cargo_json`. This ensures the HUD and CLI show "Empty" without any code changes to display layers. The `set_player_status` method continues to accept and store whatever is passed (the parser will always pass `[]`).
- **Dependencies**: None.
- **Tests**: `tests/test_adapters/test_sqlite_store.py` — add test that `get_player_status` returns empty cargo even when `cargo_json` has data in the DB.

### Unit 6: Remove dead code and update imports

- **Layer**: application, domain
- **Files**:
  - `src/tw_guidance_computer/application/parse_log_chunk.py` (already rewritten in Unit 2 — this unit removes any leftover imports)
  - `src/tw_guidance_computer/domain/models/__init__.py` (keep all exports — CargoManifest/CargoHold still used by PlayerStatus)
- **Description**: Verify no broken imports after the parser rewrite. The `CargoManifest` and `CargoHold` types remain in the domain (they're used by `PlayerStatus.cargo` field type and by the `<Info>` block tests that will be removed). The parser no longer imports `CargoManifest`, `CargoHold`, `CommodityType`, `ChatMessage`, `PortCommodity`, `TradeDirection`. Clean up any unused imports.
- **Dependencies**: Unit 2.
- **Tests**: Existing test suite passes. `mypy` passes. `ruff` passes.

## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A (parallel) | Unit 1, Unit 4, Unit 5 | Independent: port addition, intel strategy change, cargo stub |
| B (after A) | Unit 2, Unit 3 | Parser rewrite needs Unit 1's port method; store impl needs Unit 1 |
| C (after B) | Unit 6 | Cleanup after rewrite is complete |

## New Domain Types

None. All existing types are sufficient.

## New Ports

- `GameStateWriter.replace_warps_from_sector(sector_id: int, warps: list[WarpConnection]) -> None` — deletes all warps from a sector and inserts the provided complete set. Self-healing semantics.

## New Use Cases

None. `ParseLogChunk` is rewritten, not replaced.

## Adapter Changes

- **SqliteGameStateStore**: Add `replace_warps_from_sector` method. Change `import_warps` from additive to replace-per-sector-if-newer. Modify `get_player_status` to return empty cargo.
- **IntelStore port**: Update `import_warps` docstring to document new strategy.

## Risk Notes

1. **Existing parser tests will be deleted and rewritten.** The old tests cover commerce reports, transactions, and chat — all removed. New tests cover only the 5 patterns. This is intentional but means temporarily losing test coverage during the transition.

2. **Nav menu exclusion edge case**: The design review noted that indented `Ports` and `Planets` lines under nav menu entries don't have the `(T)` prefix themselves. The parser must track "in nav menu context" state and suppress parsing of these indented lines. The implementation should use a line-by-line approach for sector display detection rather than pure regex-over-full-text.

3. **Intel import warp strategy change is backward-compatible** with the CSV format — only the merge logic changes. Existing exported CSVs will import correctly under the new strategy.

4. **`get_player_status` cargo stub** means any code that previously relied on reading cargo from the DB will now see empty. This is the desired behavior per the design, but if any test asserts non-empty cargo from the reader, it will break. The parser tests that wrote cargo via `set_player_status` and then read it back will need updating.

5. **The `upsert_warp` method remains on the port** for potential future use, but the parser will no longer call it. It's still used by tests and potentially by other code paths.
