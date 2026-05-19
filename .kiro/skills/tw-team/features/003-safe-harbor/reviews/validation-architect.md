# Architect Validation: Feature 003 — Safe Harbor

**Date**: 2026-05-18
**Verdict**: PASS (with notes)

## Plan Compliance

All 9 work units are implemented as specified. The code matches the plan's architecture decisions, file locations, and behavioral requirements.

### Unit-by-Unit Assessment

| Unit | Status | Notes |
|------|--------|-------|
| 1: Domain types | ✅ PASS | `SafeHarborRoute` and `TurnThresholds` match spec exactly |
| 2: Port definition | ✅ PASS | `get_safe_sector_ids()` added to `GameStateStore` Protocol |
| 3: SQLite adapter | ✅ PASS | Uses `UNION` (implicitly DISTINCT) — correct behavior |
| 4: IniProfileStore | ✅ PASS | `get_config_value` is concrete method, not on Protocol |
| 5: FindSafeHarbor | ✅ PASS | BFS, undirected graph, sector-in-safe-set shortcut |
| 6: Alert overlay | ✅ PASS | Pure function, all three cases, truncation logic |
| 7: TUI overlay | ✅ PASS | Caching, threshold-based trigger, overlay rendering |
| 8: CLI command | ✅ PASS | Three output cases, no-status error handling |
| 9: Composition root | ✅ PASS | `resolve_config`, `resolve_db_path` wrapper, wiring |

### Minor Deviations from Plan (Acceptable)

1. **`HudDisplay` accepts `TurnThresholds | None`** — plan says required parameter, implementation makes it optional with `None` defaulting to `TurnThresholds()`. This is more robust for testing and backward compatibility. Acceptable.

2. **SQL uses `UNION` not `SELECT DISTINCT ... UNION SELECT DISTINCT`** — `UNION` already deduplicates (vs `UNION ALL`). Semantically identical, slightly cleaner. Acceptable.

## Codespec Compliance

### Hexagonal Architecture ✅

- **Dependency rule**: No violations found.
  - `find_safe_harbor.py` imports only from `application/ports` and `domain/models`
  - `alert_overlay.py` imports only from `domain/models`
  - `tui.py` imports from `domain/models` and `application` (via TYPE_CHECKING for UseCases)
  - `sqlite_store.py` imports from `application/ports` and `domain`
- **Layer placement**: All files in correct directories per the architecture.

### Domain Value Objects ✅

- Both `SafeHarborRoute` and `TurnThresholds` are `@dataclass(frozen=True)`
- Both validate in `__post_init__` raising `ValidationError` (domain exception)
- `SafeHarborRoute.hops` is a derived `@property` — correct pattern
- Re-exported from `domain/models/__init__.py` with `__all__`

### Domain Exception Hierarchy ✅

- Uses `ValidationError` which extends `GuidanceError` (the app's base exception)
- Flat hierarchy, domain-named exceptions

### Use Case Pattern ✅

- `FindSafeHarbor` is `@final`, has single `execute()` method
- Constructor injection of `GameStateStore` port
- Private helper `_build_name()` for internal logic
- Returns domain type (`SafeHarborRoute | None`)

### Port Definitions ✅

- `get_safe_sector_ids()` added to `GameStateStore` Protocol
- Returns domain type (`list[int]`)
- Docstring documents `Raises: StorageError`
- `SqliteGameStateStore` has `@override` on the implementation

### Typing Discipline ✅

- Full type annotations on all new code
- `@final` on `FindSafeHarbor`, `HudDisplay`, `SqliteGameStateStore`, `IniProfileStore`, `CliAdapter`
- `@override` on `get_safe_sector_ids` in sqlite_store
- `TurnThresholds | None` properly handled with fallback

### Composition Root ✅

- `resolve_config()` centralizes config resolution (db_path + thresholds)
- `resolve_db_path()` is a thin wrapper — backward compatible
- `AppContext` wires `FindSafeHarbor(self.store)` into `UseCases`
- Entry points (`hud.py`, `cli.py`) are thin shells calling composition functions

### Testing Strategy ✅

- Domain tests: pure validation, frozen check, derived property
- Application tests: mock port, verify BFS behavior
- Adapter tests: real SQLite for store, mock-based for CLI
- Integration test: `resolve_config` with real INI files

### Mock Separation ✅

- `test_find_safe_harbor.py`: mock creation fixture (`mock_store`), injection fixture (`find_safe_harbor`), configuration in test body
- `test_cli_commands.py`: overrides `_uc` directly in test body (pragmatic for adapter tests)

### Fixture-Centralized Construction ✅

- `find_safe_harbor` fixture constructs the use case
- `mock_store` fixture creates the mock
- Test methods contain only scenario + assertion

## Issues Found

### Minor (Non-blocking)

1. **`safe_harbor()` missing `_cli_boundary()` context manager** — Every other method in `CliAdapter` wraps its body in `with _cli_boundary():` to catch `GuidanceError` and translate to stderr + exit(1). The `safe_harbor()` method does not. If `find_safe_harbor.execute()` raises a `StorageError`, it would propagate as an unhandled exception with a traceback rather than a clean error message. The `SystemExit(1)` for no-status is fine, but the happy path is unprotected.

   **Severity**: Low. The CLI entry point's `finally: ctx.close()` ensures cleanup, and `StorageError` from SQLite is rare in practice. But it's inconsistent with the established pattern.

2. **`current_sector` parameter unused in `format_alert_overlay`** — The function accepts `current_sector: int` but never references it in the body. The plan specifies this parameter, and the TUI passes it, but it's dead code. Ruff's current rule set (`F`) doesn't flag unused function parameters (only unused variables).

   **Severity**: Cosmetic. Could be prefixed with `_` to signal intent, or removed if truly unnecessary.

3. **No test for `get_safe_sector_ids` returning empty list** — The `FindSafeHarbor` use case handles `if not safe_ids: return None` but no test exercises this path directly. The "isolated" test has safe sectors that are unreachable, which is a different code path.

   **Severity**: Low. The code is trivially correct, but a test would document the behavior.

4. **No integration test for `resolve_config` with invalid thresholds** — The plan's Risk Note #4 mentions that invalid config values propagate `ValidationError` to the entry point. There's no test verifying this error path through `resolve_config`.

   **Severity**: Low. The `TurnThresholds` validation is thoroughly tested at the domain level.

## Summary

The implementation is clean, well-structured, and conforms to both the implementation plan and codespecs. The dependency rule is respected throughout. Domain types are properly validated and immutable. The use case is correctly isolated with port-based dependency injection. The composition root centralizes wiring. Tests cover the critical paths.

The only actionable item is #1 (missing `_cli_boundary()`) which represents a minor inconsistency in error handling. The other notes are cosmetic or coverage gaps that don't affect correctness.
