# Implementation Plan Review: Profile-Based Configuration

**Reviewer**: Architect (Adversary Mode)
**Date**: 2025-05-17
**Verdict**: FAIL

## Critical Issues

### 1. `Path` in Domain Layer — I/O Coupling

The plan puts `db_path: Path` on the `Profile` domain value object and defines a class method `default_db_path(name: str) -> Path` that calls `Path.home()`.

**Problem**: `Path.home()` is an I/O operation — it reads the `HOME` environment variable or queries the OS. The Domain-Value-Objects codespec says value objects carry "no behavior beyond derived properties" and the Hexagonal-Architecture codespec says domain has "Zero external dependencies — no frameworks, no I/O." While `pathlib` itself is stdlib and acceptable for *data representation*, `Path.home()` performs a system call. A class method that generates filesystem paths based on OS state is infrastructure logic, not domain logic.

**Additionally**: No existing domain model in this project uses `Path`. All domain models use primitive types (`int`, `str`, `float`) or other domain types. Introducing `Path` as a domain field type is a precedent that should be questioned — the domain doesn't care about filesystem paths. It cares about a profile having a name and a storage location identifier (which is a string).

**Fix**: `Profile` should have `name: str` and `db_path: str`. The default path generation logic (`~/.local/share/tw-guidance-computer/{name}.db`) belongs in the adapter (`IniProfileStore`) or the composition root — it's a convention about where files live on disk, not a business rule.

### 2. `default_db_path` Class Method Violates Value Object Rules

The codespec for Domain Value Objects (Rule 4) says: "Derived properties are fine. Read-only `@property` methods that compute values from the object's fields belong on the value object."

A `@classmethod` that generates a path from a name parameter is NOT a derived property — it doesn't compute from the object's own fields. It's a factory/construction helper. The plan explicitly calls this "domain behavior" to justify putting it in the domain layer, but it's actually infrastructure convention (where to put DB files on this OS).

**Fix**: Move `default_db_path` to the adapter or a helper in the composition root. The domain `Profile` is just `name` + `db_path` with validation on `name`.

### 3. `ListProfiles` Use Case Return Type Violates Codespec

The plan says `ListProfiles.execute()` returns `tuple[list[Profile], str]`. The Use-Case-Pattern codespec (Rule 8) says: "Structured data always gets a value object — never a raw tuple, dict, or untyped collection."

A `tuple[list[Profile], str]` is exactly the kind of untyped collection the codespec prohibits. What is that `str`? The default profile name. This should be a proper value object (e.g., `ProfileList` with `profiles: list[Profile]` and `default_name: str`).

**Fix**: Define a `ProfileListing` value object or have the use case return `list[Profile]` with a `is_default: bool` field on `Profile` itself.

### 4. Unit 7 — Modifying `CliAdapter` Constructor Creates Coupling Concern

The plan says: "CliAdapter.__init__ gains optional parameters for the profile use cases (or a second small container)."

The current `CliAdapter` takes `UseCases` — a frozen typed container. Adding optional profile use cases as separate constructor parameters breaks the pattern. The plan is vague here ("or a second small container") which suggests the architect hasn't decided.

**Fix**: Either add `CreateProfile` and `ListProfiles` to the `UseCases` container (they ARE use cases), or create a separate `ProfileCliAdapter` that handles only profile commands. The latter is cleaner since profile commands don't need `AppContext` (they don't need the DB).

### 5. Composition Root Calls Adapter Directly — Justified but Under-Specified

The plan says `resolve_db_path()` in `compose.py` constructs `IniProfileStore` and calls it directly. This is acceptable (composition root knows about adapters), but the plan doesn't address:

- What happens if the config file is malformed? Does `resolve_db_path` catch `ConfigError` and print to stderr? Or does it propagate?
- The current `cli.py` checks `if not args.db.exists()` and exits with a helpful message. With profiles, who checks if the resolved DB path exists? The plan removes this check but doesn't replace it.

**Fix**: Specify error handling in `resolve_db_path`. The entry point should catch `ConfigError` and `ProfileNotFoundError` and print user-friendly messages before exiting.

### 6. Unit 6 and Unit 8 Have a Hidden Dependency

The plan puts Unit 6 (IniProfileStore) in parallel group C with Units 4 and 5. But Unit 8 (composition root) calls `IniProfileStore` directly for profile resolution. The plan says Unit 8 depends on "all previous units" — correct. But the *design* of Unit 6's public API is also constrained by Unit 8's needs (the `resolve_db_path` function needs a specific method signature). This isn't a parallelism conflict (they're in different groups), but it means Unit 6's API must be designed with Unit 8's consumption pattern in mind. The plan should make this explicit.

### 7. Auto-Migration Logic Location is Ambiguous

The plan says auto-migration (creating config.ini on first run) lives in `IniProfileStore`. But it also says the composition root calls `resolve_db_path` which constructs `IniProfileStore`. So auto-migration happens as a side effect of adapter construction or first method call?

**Problem**: Side effects in constructors violate the principle that construction and use are separate. If `IniProfileStore.__init__` creates the config file, that's I/O in a constructor. If it happens on first `get_profile()` call, that's surprising behavior for a read operation.

**Fix**: Make auto-migration an explicit method (`ensure_config_exists()`) called by the composition root before resolving the profile. This keeps the side effect visible and intentional in the wiring code.

## Minor Issues

### 8. Profile Name Validation Regex is Under-Specified

The plan says "contain only `[a-z0-9-]`, not start/end with hyphen" but doesn't specify a maximum length. Profile names become part of filesystem paths (`{name}.db`). Extremely long names could hit filesystem limits. Add a reasonable max length (e.g., 64 chars).

### 9. `ConfigError` vs Existing `StorageError`

The plan adds `ConfigError(GuidanceError)`. The existing codebase already has `StorageError(GuidanceError)` for "persistent storage is unavailable or fails." A config file IS persistent storage. Is `ConfigError` distinct enough to warrant a separate exception? The answer is probably yes (config errors are user-fixable, storage errors are system failures), but the plan should justify the distinction.

### 10. Risk Note #5 — Special-Casing "default" Name

The plan notes that `default_db_path("default")` should return `game.db` instead of `default.db` for migration compatibility. This is a business rule buried in a risk note rather than specified in the domain model's behavior. If this special case exists, it must be in the implementation plan's Unit 1 description and tested.

## Staff Engineer Constraint Validation

| Constraint | Status |
|-----------|--------|
| Config must NOT become a god object | ✅ PASS — `AppContext` still takes `db_path: Path`, not a config object |
| Config resolved in composition root, discrete values downstream | ✅ PASS — `resolve_db_path()` extracts the path, passes it as `Path` |
| Profile has domain behavior | ⚠️ PARTIAL — Name validation is legitimate domain behavior. Path generation is NOT (it's infrastructure convention). |
| Hexagonal architecture followed strictly | ❌ FAIL — `Path.home()` in domain, class method that's not a derived property |

## Summary

The plan's overall architecture is sound — the separation between profile resolution (composition root) and profile management (use cases) is correct. The dependency rule is respected for the most part. But the plan puts infrastructure logic (`Path.home()`, filesystem path conventions) in the domain layer and uses a raw tuple as a use case return type. These are codespec violations that need correction before building.

## Required Changes for PASS

1. Remove `Path` from `Profile` domain model — use `str` for `db_path`
2. Move `default_db_path()` out of domain — into adapter or composition root
3. Replace `tuple[list[Profile], str]` return with a proper value object
4. Decide on `CliAdapter` modification approach (add to `UseCases` container or separate adapter)
5. Make auto-migration an explicit step in the composition root, not a side effect
6. Specify error handling for `resolve_db_path` in entry points
7. Document the "default" → "game.db" special case in Unit 1, not just risk notes

---

# Second-Pass Adversarial Review

**Reviewer**: Architect (Adversary Mode, Pass 2)
**Date**: 2025-05-17
**Verdict**: PASS (with minor observations)

## Required Change Verification

### 1. ✅ Remove `Path` from `Profile` domain model — use `str` for `db_path`

**Status**: ADDRESSED. Unit 1 explicitly states: "Frozen dataclass `Profile` with fields `name: str` and `db_path: str`." The plan further clarifies: "The `db_path` field is a plain string — the domain doesn't know about filesystem paths, only that a profile has a storage location identifier." The `str` → `Path` conversion happens in the composition root (`resolve_db_path` returns `Path(profile.db_path)`). This is correct — the boundary between string representation and filesystem type happens at the wiring layer.

### 2. ✅ Move `default_db_path()` out of domain — into adapter or composition root

**Status**: ADDRESSED. The plan places path generation in `IniProfileStore.resolve_default_db_path(name: str) -> str` (adapter) and `default_config_path() -> Path` in `compose.py` (composition root). The architecture decision section explicitly states: "Default DB path generation (infrastructure convention: 'DB files go in ~/.local/share/tw-guidance-computer/'). This is where-files-live-on-disk knowledge, not a business rule." No path generation logic remains in the domain layer.

### 3. ✅ Replace `tuple[list[Profile], str]` return with a proper value object

**Status**: ADDRESSED. Unit 3 introduces `ProfileListing` — a frozen dataclass with `profiles: list[Profile]` and `default_name: str`, plus a derived property `default_profile -> Profile | None`. Unit 6 (`ListProfiles`) returns `ProfileListing`. This satisfies the Use-Case-Pattern codespec Rule 8.

### 4. ✅ Decide on `CliAdapter` modification approach

**STATUS**: ADDRESSED. Unit 8 makes the explicit decision: "Add `CreateProfile` and `ListProfiles` as optional fields on the `UseCases` container." Rationale is provided (they ARE use cases, established pattern). Optional fields (`CreateProfile | None = None`) preserve backward compatibility. The plan also specifies that profile CLI methods check for None.

### 5. ✅ Make auto-migration an explicit step in the composition root

**Status**: ADDRESSED. Unit 7 states: "`ensure_config_exists()`: If config file doesn't exist, creates directory and writes initial config... Called explicitly by the composition root — NOT a constructor side effect." Unit 9 confirms the sequence: "1. Constructs `IniProfileStore(...)` 2. Calls `store.ensure_config_exists()` — explicit, visible migration step." The architecture decision section reinforces: "Calling `ensure_config_exists()` then resolving the profile — explicit, visible side effects in wiring code."

### 6. ✅ Specify error handling for `resolve_db_path` in entry points

**Status**: ADDRESSED. Unit 9 specifies:
- `ConfigError` → print `"Error: Failed to parse config: {details}"` to stderr, exit 1
- `ProfileNotFoundError` → print `"Error: Profile '{name}' not found. Run 'tw profile list' to see available profiles."` to stderr, exit 1
- Described as "user-facing errors with actionable messages"

This matches the existing pattern in `cli.py` where `_cli_boundary()` catches `GuidanceError` and prints to stderr.

### 7. ✅ Document the "default" → "game.db" special case in the adapter unit

**Status**: ADDRESSED. Unit 7 explicitly documents: "`resolve_default_db_path(name: str) -> str`: Returns `~/.local/share/tw-guidance-computer/game.db` if name is `"default"`, otherwise `~/.local/share/tw-guidance-computer/{name}.db`. This is infrastructure convention (where files live on disk), correctly placed in the adapter." Also specified in tests: "resolve_default_db_path returns `game.db` for 'default' and `{name}.db` otherwise." Risk Note #5 still exists but now references the adapter unit rather than being the sole documentation.

## Codespec Compliance Check

| Codespec | Status | Notes |
|----------|--------|-------|
| Hexagonal Architecture | ✅ | Domain has no I/O, no Path.home(). Application depends only on domain + ports. Adapters implement ports. Composition root wires. |
| Domain Value Objects | ✅ | `Profile` and `ProfileListing` are frozen dataclasses with `__post_init__` validation raising `ValidationError`. Derived property on `ProfileListing`. Uses `str` not `Path`. |
| Domain Exception Hierarchy | ✅ | New exceptions extend `GuidanceError`. Flat hierarchy. `ConfigError` justified as distinct from `StorageError`. |
| Use Case Pattern | ✅ | `CreateProfile` and `ListProfiles` are `@final`, single `execute()` method, constructor-injected port, return domain types. |
| Port Definitions | ⚠️ | See observation below. |
| Composition Root | ✅ | `resolve_db_path` lives in compose.py. Construction isolated. `AppContext` signature unchanged. |
| Fixture-Centralized Construction | ✅ | Test requirements specified per unit. |
| Typing Discipline | ✅ | `@final` on use cases, `@override` on adapter methods implied by port implementation. |
| Minimal Dependencies | ✅ | Uses only `configparser` (stdlib). No new external dependencies. |

## Staff Engineer Constraint Validation

| Constraint | Status |
|-----------|--------|
| Config must NOT become a god object | ✅ — `AppContext` still takes `db_path: Path`, not a config object |
| Config resolved in composition root, discrete values downstream | ✅ — `resolve_db_path()` extracts the path, passes it as `Path` |
| Profile has domain behavior | ✅ — Name validation is legitimate domain behavior in `__post_init__` |
| Hexagonal architecture followed strictly | ✅ — No I/O in domain, path generation in adapter |

## Minor Observations (non-blocking)

### A. `resolve_default_db_path` on the `ProfileStore` port — mixed concern

The `ProfileStore` port has 5 methods. Four are persistence operations (`get_profile`, `list_profiles`, `save_profile`, `ensure_config_exists`). One is a pure computation (`resolve_default_db_path`) — it generates a path string from a name using a naming convention. This method doesn't read or write the config file.

**Why it's acceptable**: The naming convention ("default" → "game.db") is tightly coupled to the config file's semantics. The adapter that writes `[profile:default] db = .../game.db` is the same adapter that knows this convention. Putting it on the port keeps the convention co-located with the persistence logic that uses it. The alternative (a standalone function in compose.py) would scatter the convention across two files.

**Observation only** — not a violation. The port still speaks domain types (returns `str`), and the method is documented.

### B. Optional fields on `UseCases` container

Adding `create_profile: CreateProfile | None = None` and `list_profiles: ListProfiles | None = None` to the frozen `UseCases` dataclass means every existing construction site (compose.py's `AppContext.__init__`) will use the defaults without change. This is backward-compatible.

However, the `CliAdapter` must now handle the `None` case at runtime. The plan says "profile CLI methods check for None and print an error if somehow called without wiring." This is a defensive check that should never trigger in practice (the composition root always wires them for CLI). It's fine as a safety net but the test should verify the wired path, not the None path.

### C. Unit 4 port includes `ensure_config_exists()` — side-effect method on a Protocol

`ensure_config_exists()` is a side-effect method (creates files). Having it on the port means the application layer *could* call it, even though the plan only calls it from the composition root. This is acceptable because:
1. The composition root needs to call it through the adapter instance
2. The port is the adapter's contract — it documents what the adapter can do
3. No use case calls it

If a future developer adds a use case that calls `ensure_config_exists()`, that would be a code review catch, not an architectural violation.

### D. Parallel group ordering is conservative but correct

Units 5, 6, and 7 are in the same parallel group (D). Unit 5 (`CreateProfile`) calls `store.resolve_default_db_path()` which is defined in Unit 4 (port) and implemented in Unit 7 (adapter). Since Unit 5 only depends on the *port definition* (Unit 4, group C), not the *implementation* (Unit 7), they can genuinely run in parallel. The builder for Unit 5 mocks the port; the builder for Unit 7 implements it. No file conflicts. Correct.

## Verdict: PASS

All 7 required changes have been addressed. The revised plan conforms to codespecs, respects the dependency rule, keeps I/O out of domain and application layers, and follows established project patterns. No new issues introduced. Ready for build phase.
