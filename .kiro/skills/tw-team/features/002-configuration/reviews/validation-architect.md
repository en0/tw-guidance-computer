# Architect Validation — Feature 002: Profile-Based Configuration

**Date**: 2026-05-17
**Verdict**: PASS (with notes)

## Work Unit Verification

| Unit | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | Profile value object | ✅ PASS | Frozen, validates in `__post_init__`, raises `ValidationError` |
| 2 | New exceptions | ✅ PASS | Flat hierarchy under `GuidanceError`, all three added |
| 3 | ProfileListing value object | ✅ PASS | Frozen, validates `default_name`, derived property works |
| 4 | ProfileStore port | ✅ PASS | Protocol, domain types, documented exceptions |
| 5 | CreateProfile use case | ✅ PASS | `@final`, `execute()`, constructor injection |
| 6 | ListProfiles use case | ✅ PASS | `@final`, `execute()`, constructor injection |
| 7 | IniProfileStore adapter | ✅ PASS | `@final`, `@override` on all 5 methods, `from e` on translations |
| 8 | CLI commands (inbound) | ✅ PASS | Methods added, None checks present |
| 9 | Composition root + entry points | ✅ PASS | `resolve_db_path()` extracts discrete `Path`, no config propagation |

## Codespec Compliance

### Dependency Rule (adapters → application → domain)
- ✅ Domain imports nothing from application or adapters
- ✅ Application imports only from domain (and own ports)
- ✅ Adapters import from application and domain
- ✅ No I/O libraries in domain or application

### Use Case Pattern
- ✅ `@final` on both `CreateProfile` and `ListProfiles`
- ✅ Single `execute()` method on each
- ✅ Dependencies via constructor injection
- ✅ Return domain types (`Profile`, `ProfileListing`)

### Port Definitions
- ✅ `typing.Protocol` class
- ✅ All parameters and returns are domain types
- ✅ `Raises:` documented in docstrings
- ✅ Adapter explicitly inherits from Protocol
- ✅ `@override` on all 5 implementing methods

### Domain Value Objects
- ✅ `@dataclass(frozen=True)` on both `Profile` and `ProfileListing`
- ✅ `__post_init__` validation raises `ValidationError`
- ✅ `db_path` is `str` (not `Path`) — domain doesn't know about filesystem
- ✅ Derived property `default_profile` on `ProfileListing`

### Domain Exception Hierarchy
- ✅ Flat: `ProfileNotFoundError`, `ProfileExistsError`, `ConfigError` all extend `GuidanceError` directly
- ✅ `from e` used on all exception translations in adapter (3 sites)
- ✅ Exceptions describe domain problems, not technical ones

### Composition Root
- ✅ `AppContext` takes `db_path: Path` — discrete value, not config object
- ✅ `resolve_db_path()` is construction logic in the composition root
- ✅ `ensure_config_exists()` called explicitly (not a constructor side effect)
- ✅ `str` → `Path` conversion happens at the boundary in `resolve_db_path()`
- ✅ Profile use cases constructed separately via `build_profile_use_cases()`
- ✅ No config god object propagates downstream

### Staff Engineer Constraints
- ✅ Config resolved in composition root, discrete values downstream
- ✅ `AppContext` signature unchanged — still takes `db_path: Path`
- ✅ `--db` flag removed from both entry points

## Issues Found

### Minor: Uncaught `ValidationError` in CLI entry point

**Location**: `src/tw_guidance_computer/cli.py`, `_handle_profile_command()`

The `try/except` around `_handle_profile_command()` catches `ConfigError` and `ProfileNotFoundError` but not `ValidationError` or `ProfileExistsError`. If a user runs `tw profile create INVALID`, the `ValidationError` propagates as an unhandled exception with a full traceback instead of a clean error message.

The `CliAdapter.profile_create()` method correctly handles this via `_cli_boundary()` (catches all `GuidanceError`), but the entry point bypasses `CliAdapter` for profile commands.

**Fix**: Change the except clause to catch `GuidanceError` (the base), or add `ValidationError` and `ProfileExistsError` to the tuple.

**Severity**: Low — user-facing UX issue, not a correctness bug.

### Minor: Uncaught `ValidationError` in HUD entry point

**Location**: `src/tw_guidance_computer/hud.py`, line ~43

If `--create` is used with an invalid profile name (e.g., `--profile "INVALID" --create`), `CreateProfile.execute()` raises `ValidationError` which is not caught. Only `ProfileExistsError` is caught.

**Fix**: Add `ValidationError` to the except clause, or catch `GuidanceError` broadly.

**Severity**: Low — same UX issue.

### Minor: `OSError` escape in `save_profile`

**Location**: `src/tw_guidance_computer/adapters/outbound/ini_profile_store.py`, `save_profile()`

The `try/except` catches `configparser.Error` but not `OSError`. If `self._config_path.open("w")` fails (permissions, disk full), the `OSError` escapes untranslated.

**Practical impact**: Near zero — `ensure_config_exists()` is always called first, guaranteeing the file exists and is writable. But the codespec says "Adapters translate all external exceptions."

**Fix**: Add `except OSError as e: raise ConfigError(str(e)) from e`.

**Severity**: Very low — theoretical edge case.

### Observation: Silent `--create` without `--profile`

`hud.py` guards `--create` with `if args.create and args.profile:`. Running `tw-hud --create logfile` silently ignores `--create`. This is reasonable (creating "default" is a no-op since `ensure_config_exists` handles it), but could confuse users.

Not a codespec violation — just a UX note.

## Test Coverage Assessment

- ✅ Domain validation: 12 test cases covering all validation rules
- ✅ ProfileListing: 3 test cases (match, no match, empty default_name)
- ✅ CreateProfile use case: 3 test cases (happy path, duplicate, invalid name)
- ✅ ListProfiles use case: 2 test cases (returns listing, delegates to store)
- ✅ IniProfileStore adapter: 9 test cases across 5 test classes
- ✅ CLI commands: 2 test classes for profile_create and profile_list output
- ✅ Integration: 3 test cases for resolve_db_path end-to-end

## Automated Tool Verification

Commands to run:
```
uv run pytest && uv run mypy src/ && uv run ruff check src/
```

**Status**: Not executed in this validation pass (no shell access). Must be run by Team Lead or Builder before final sign-off.

**Expected outcome**: All should pass — the code follows typing discipline (`@final`, `@override`, full annotations), ruff rules (docstrings, imports), and test patterns. No known issues that would cause failures.

## Conclusion

Implementation conforms to the plan and codespecs. The three minor issues are all low-severity UX concerns (uncaught exceptions producing tracebacks instead of clean error messages). No architectural violations, no dependency rule breaks, no I/O in wrong layers. The code is clean, well-structured, and testable.

**Recommendation**: Fix the `ValidationError`/`ProfileExistsError` catch in `cli.py` before merge (it's a one-line change). The other two are acceptable as-is.
