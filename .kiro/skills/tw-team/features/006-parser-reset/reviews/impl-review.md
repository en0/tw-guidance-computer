# Implementation Plan Review: Feature 006 — Parser Reset

**Reviewer**: Architect (Adversary Mode)
**Date**: 2025-05-24
**Verdict**: PASS (with notes)

## Summary

The plan is architecturally sound. It respects the dependency rule, keeps business logic in the application layer, isolates I/O in adapters, and uses domain types at all boundaries. The work unit decomposition is logical with correct dependency ordering. The parallel execution plan is safe — no file conflicts between parallel units.

## Issues Found

### Issue 1: `import_warps` strategy change spans two layers in one unit (MINOR)

**Unit 4** modifies both `sqlite_store.py` (adapter) and `intel_store.py` (application port). The plan says to "update the IntelStore Protocol docstring" — this is fine since it's just documentation, not a signature change. However, the plan should be explicit that the `import_warps` method signature does NOT change (same args, same return type). The behavioral change is entirely in the adapter implementation.

**Impact**: Low. The plan implies this but doesn't state it explicitly. A builder could misinterpret and try to change the Protocol signature.

**Recommendation**: Add a note: "The `import_warps` method signature is unchanged. Only the implementation strategy and docstring change."

### Issue 2: `replace_warps_from_sector` uses `list[WarpConnection]` — correct but verify (NOTE)

The port method signature `replace_warps_from_sector(sector_id: int, warps: list[WarpConnection]) -> None` speaks domain types (good). The `sector_id` parameter is redundant with `warp.from_sector` for each warp in the list. This is acceptable — the sector_id drives the DELETE, and the warps provide the INSERT data. But the implementation must validate or document that all warps in the list have `from_sector == sector_id`.

**Impact**: Low. Edge case — if the parser constructs warps correctly this never matters. But the port contract should document the precondition.

**Recommendation**: Docstring should state: "All warps in the list must have `from_sector == sector_id`."

### Issue 3: Cargo stub in `get_player_status` is adapter-level behavior masking stored data (NOTE)

**Unit 5** makes `get_player_status` always return `cargo=[]` regardless of DB contents. This is a deliberate design choice per the feature design, but it means the adapter is now lying about what's stored. This is acceptable as a transitional measure (the parser will always write `[]` anyway), but it creates a subtle inconsistency: `set_player_status` accepts and stores cargo, but `get_player_status` discards it on read.

**Impact**: Low. The design explicitly calls for this. It's a temporary state until cargo tracking is re-implemented.

**Recommendation**: Add a code comment in the adapter: `# Cargo tracking disabled (Feature 006). Always returns empty.`

### Issue 4: `add_chat_message` remains on `GameStateWriter` but parser won't call it (NOTE)

The parser rewrite removes chat extraction, but `add_chat_message` stays on the `GameStateWriter` Protocol. This is correct — the port defines the store's capabilities, not what the parser uses. But Unit 6 (dead code cleanup) should verify no orphaned imports of `ChatMessage` remain in the rewritten parser.

**Impact**: None. The port is stable; unused methods are fine on a Protocol.

### Issue 5: Nav menu exclusion — line-by-line vs. regex-over-full-text not specified (MINOR)

Unit 2 describes the nav menu exclusion mechanism but doesn't specify the implementation approach clearly enough for a builder. The risk note (#2) mentions "line-by-line approach" but the unit description mixes regex patterns with state tracking ("nav menu active" flag). The builder needs a clear algorithm:

1. Split text into lines
2. For each line, check if it matches `^\s*\([TS*\d]\)\s*Sector`
3. If yes, set nav_active flag, skip
4. If nav_active and line is indented (starts with spaces) and matches Ports/Planets, skip
5. If line matches bare `Sector\s+:` (no prefix, no indent), clear nav_active, process normally
6. Command prompt also clears nav_active

**Impact**: Medium. Ambiguous spec could lead to incorrect implementation. The nav menu exclusion is the core bug fix of this feature.

**Recommendation**: Add a pseudocode algorithm to Unit 2's description.

### Issue 6: Unit 2 test list missing edge case — sector display immediately after nav menu (MINOR)

The test classes listed for Unit 2 include `TestNavMenuExclusion` but don't explicitly call out the transition case: a real sector display appearing on the line immediately after a nav menu block ends. This is the most likely regression scenario.

**Impact**: Low. A good builder would include this, but it should be explicit.

**Recommendation**: Add to `TestNavMenuExclusion`: "Real sector display after nav menu block is parsed correctly."

## Dependency Rule Validation

| Layer | Imports From | Violation? |
|-------|-------------|-----------|
| Domain (unchanged) | Nothing | ✓ |
| Application (Unit 2) | Domain types, application ports | ✓ |
| Adapters (Units 3, 4, 5) | Application ports, domain types | ✓ |

No violations found.

## Parallel Conflict Check

| Group A (parallel) | Files Modified |
|---|---|
| Unit 1 | `application/ports/game_state_writer.py` |
| Unit 4 | `adapters/outbound/sqlite_store.py`, `application/ports/intel_store.py` |
| Unit 5 | `adapters/outbound/sqlite_store.py` |

**Conflict**: Units 4 and 5 both modify `sqlite_store.py`. They touch different methods (`import_warps` vs `get_player_status`) so the conflict is merge-level only, not semantic. A builder doing them sequentially within Group A avoids this.

**Recommendation**: Note in the parallel plan that Units 4 and 5 should be done sequentially within Group A (or acknowledge the merge conflict risk).

## Codespec Compliance

| Spec | Status |
|------|--------|
| Hexagonal Architecture | ✓ Layers respected, port in application, impl in adapter |
| Domain Value Objects | ✓ No new domain types needed; existing ones unchanged |
| Domain Exception Hierarchy | ✓ StorageError used at adapter boundary |
| Port Definitions | ✓ Protocol method with domain types, `@override` on impl |
| Use Case Pattern | ✓ ParseLogChunk remains @final with execute() |
| Composition Root | ✓ No composition changes needed |
| Testing Strategy | ✓ Tests mirror source, one behavior per test |
| Mock Separation | ✓ Parser tests mock the port, adapter tests use real DB |
| Typing Discipline | ✓ @override on new adapter method |
| Minimal Dependencies | ✓ No new dependencies |

## Verdict

**PASS** — The plan is well-structured, architecturally compliant, and correctly decomposed. The issues found are minor clarifications that reduce ambiguity for the builder but don't represent architectural flaws or codespec violations. The one medium-impact item (nav menu algorithm clarity) is a documentation gap, not a design flaw.

### Required Before Build
- None (all issues are recommendations, not blockers)

### Recommended Before Build
1. Clarify that `import_warps` signature is unchanged (Issue 1)
2. Add pseudocode for nav menu exclusion algorithm (Issue 5)
3. Note Units 4+5 file conflict in parallel plan (Parallel Conflict Check)
