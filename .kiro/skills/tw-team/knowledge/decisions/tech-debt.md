# Technical Debt

## Entry Point Doing Composition Root Work

**Found**: 2026-05-18
**Severity**: Codespec violation (Composition Root rule 2: "Entry points are thin shells")
**Status**: Unfixed

### Problem

`hud.py` and `cli.py` call `resolve_config()` / `resolve_db_path()` themselves, then pass the results back into `AppContext`. This is the entry point doing construction logic that belongs entirely in the composition root.

### Where

- `src/tw_guidance_computer/hud.py` — calls `resolve_config(args.profile)`, passes `db_path` and `thresholds` separately
- `src/tw_guidance_computer/cli.py` — calls `resolve_db_path(args.profile)`, passes `db_path` to `AppContext`

### Fix

`AppContext.__init__` should accept `profile_name: str | None` and handle config resolution internally. Entry points just pass the profile name. `AppContext` exposes `thresholds` as an attribute for the HUD to read.

### Likely Related Violations (audit needed)

- [ ] `cli.py` checks `if not db_path.exists()` — that's a construction concern, belongs in AppContext
- [ ] `hud.py` constructs `build_profile_use_cases()` directly for `--create` — should this be in the root?
- [ ] `resolve_db_path` existing as a separate public function may be unnecessary if AppContext owns resolution
- [ ] Feature 002 introduced this pattern — check if the original `resolve_db_path` design was already wrong
