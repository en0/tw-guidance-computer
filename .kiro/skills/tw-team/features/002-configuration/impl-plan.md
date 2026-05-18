# Implementation Plan: Profile-Based Configuration

## Overview

Replace the `--db` flag with a profile system backed by an INI config file at `~/.config/tw-guidance-computer/config.ini`. Profiles store per-server settings (currently just `db` path). The composition root resolves the active profile and passes discrete values (`db_path: Path`) to adapters — no config object propagates through the system.

## Architecture Decision: Where Does Profile Live?

**The interesting question**: Profile has business rules (name validation) but its persistence is a config file, not the database. How does this map to hexagonal architecture?

**Answer**: Profile is a **domain value object** — it has validation rules (name format constraints). The config file is an **outbound adapter** implementing a `ProfileStore` port. The use cases `CreateProfile` and `ListProfiles` orchestrate the domain logic and persistence through the port.

The composition root is the consumer of this system: it calls the adapter directly (not through a use case) to resolve the active profile's `db_path` at startup. The use cases exist only for the `tw profile create` and `tw profile list` CLI commands.

**What belongs where:**
- **Domain**: Profile name validation (business rule: "names must be lowercase alphanumeric with hyphens, 1-64 chars, no leading/trailing hyphens")
- **Adapter/Composition root**: Default DB path generation (infrastructure convention: "DB files go in `~/.local/share/tw-guidance-computer/`"). This is where-files-live-on-disk knowledge, not a business rule.
- **Adapter**: Auto-migration (creating config.ini with default profile pointing to legacy DB path)
- **Composition root**: Calling `ensure_config_exists()` then resolving the profile — explicit, visible side effects in wiring code

**Why the composition root reads the adapter directly for resolution**: Reading the active profile's DB path at startup is *wiring*, not a business operation. The composition root already knows about adapters (it constructs them). Having it call `profile_store.get_profile(name)` to get a `Profile` value object, then extract `profile.db_path` to pass into `AppContext`, is the correct pattern — it's construction logic, not application logic.

## Work Units

### Unit 1: Domain — Profile Value Object

- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/models/profile.py`, update `domain/models/__init__.py`
- **Description**: Frozen dataclass `Profile` with fields `name: str` and `db_path: str`. Validates name in `__post_init__`: non-empty, max 64 chars, matches `[a-z0-9-]`, must not start or end with hyphen. Raises `ValidationError` on failure. The `db_path` field is a plain string — the domain doesn't know about filesystem paths, only that a profile has a storage location identifier.
- **Special case — "default" name**: The name `"default"` is valid. The mapping of `"default"` → `game.db` (instead of `default.db`) is an infrastructure convention handled by the adapter's path generation, NOT domain logic.
- **Dependencies**: None.
- **Tests**: `tests/test_domain/test_profile.py` — validation rejects empty names, names with spaces/uppercase/special chars, names starting/ending with hyphens, names > 64 chars. Accepts valid names like `"saintcon"`, `"my-server-1"`, `"default"`.

### Unit 2: Domain — New Exceptions

- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/exceptions.py`
- **Description**: Add `ProfileNotFoundError(GuidanceError)`, `ProfileExistsError(GuidanceError)`, `ConfigError(GuidanceError)`. Justification for `ConfigError` vs existing `StorageError`: config errors are user-fixable (edit the INI file) while storage errors are system failures (disk full, permissions). Different recovery actions warrant different exception types.
- **Dependencies**: None.
- **Tests**: Covered by use case and adapter tests.

### Unit 3: Domain — ProfileListing Value Object

- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/models/profile.py` (same file as Profile), update `domain/models/__init__.py`
- **Description**: Frozen dataclass `ProfileListing` with fields `profiles: list[Profile]` and `default_name: str`. This replaces the raw `tuple[list[Profile], str]` that the adversary flagged. Validates that `default_name` is non-empty. Provides a derived property `default_profile -> Profile | None` that finds the profile matching `default_name` in the list.
- **Dependencies**: Unit 1 (uses `Profile` type).
- **Tests**: `tests/test_domain/test_profile.py` — `default_profile` property returns correct profile or None.

### Unit 4: Application — ProfileStore Port

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/ports/profile_store.py`
- **Description**: Protocol defining the config file abstraction. Methods:
  - `get_profile(name: str) -> Profile` — raises `ProfileNotFoundError`
  - `list_profiles() -> ProfileListing` — returns all profiles with default name
  - `save_profile(profile: Profile) -> None` — raises `ProfileExistsError` if exists
  - `ensure_config_exists() -> None` — creates config file with default profile if missing; no-op if exists
  - `resolve_default_db_path(name: str) -> str` — generates the conventional DB path string for a profile name (handles "default" → "game.db" special case)
- **Dependencies**: Unit 1, Unit 3 (uses `Profile` and `ProfileListing` types).
- **Tests**: Tested via adapter and use case tests.

### Unit 5: Application — CreateProfile Use Case

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/create_profile.py`
- **Description**: `@final` class with `execute(name: str) -> Profile`. Constructs `Profile(name=name, db_path=self._store.resolve_default_db_path(name))` — construction triggers domain validation on the name. Persists via `ProfileStore.save_profile()`. Returns the created `Profile`.
- **Dependencies**: Unit 1, Unit 2, Unit 4.
- **Tests**: `tests/test_application/test_create_profile.py` — happy path returns Profile, duplicate name raises `ProfileExistsError`, invalid name raises `ValidationError`.

### Unit 6: Application — ListProfiles Use Case

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/list_profiles.py`
- **Description**: `@final` class with `execute() -> ProfileListing`. Delegates to `ProfileStore.list_profiles()`. Returns the `ProfileListing` value object directly.
- **Dependencies**: Unit 3, Unit 4.
- **Tests**: `tests/test_application/test_list_profiles.py` — returns ProfileListing with profiles and default name.

### Unit 7: Adapter — IniProfileStore (outbound)

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/ini_profile_store.py`
- **Description**: Implements `ProfileStore` using `configparser`. Reads/writes `~/.config/tw-guidance-computer/config.ini`.

  **Key behaviors:**
  - `ensure_config_exists()`: If config file doesn't exist, creates directory and writes initial config with `[DEFAULT] default_profile = default` and `[profile:default] db = ~/.local/share/tw-guidance-computer/game.db`. This is the auto-migration path. Called explicitly by the composition root — NOT a constructor side effect.
  - `resolve_default_db_path(name: str) -> str`: Returns `~/.local/share/tw-guidance-computer/game.db` if name is `"default"`, otherwise `~/.local/share/tw-guidance-computer/{name}.db`. This is infrastructure convention (where files live on disk), correctly placed in the adapter.
  - `get_profile(name: str) -> Profile`: Reads `[profile:{name}]` section, expands `~` in the `db` value, returns `Profile(name=name, db_path=expanded_path)`. Raises `ProfileNotFoundError` if section missing.
  - `list_profiles() -> ProfileListing`: Reads all `[profile:*]` sections, reads `default_profile` from `[DEFAULT]`, returns `ProfileListing`.
  - `save_profile(profile: Profile) -> None`: Writes `[profile:{name}]` section. Raises `ProfileExistsError` if section already exists.

  **Error translation**: All `configparser` errors (MissingSectionHeaderError, ParsingError, etc.) are caught and raised as `ConfigError` with `from e`.

  **API constraint**: Unit 8 (composition root) calls `ensure_config_exists()` then `get_profile()`. The `resolve_default_db_path` method signature must support this consumption pattern.

- **Dependencies**: Unit 1, Unit 2, Unit 3, Unit 4.
- **Tests**: `tests/test_adapters/test_ini_profile_store.py` — reads/writes INI in tmp_path, `ensure_config_exists` creates default config, handles malformed files with `ConfigError`, `resolve_default_db_path` returns `game.db` for "default" and `{name}.db` otherwise, `~` expansion works.

### Unit 8: Inbound Adapter — Profile CLI Commands

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/inbound/cli_commands.py` (extend existing)
- **Description**: Add `profile_create(name: str)` and `profile_list()` methods to `CliAdapter`.

  **Approach decision**: Add `CreateProfile` and `ListProfiles` as optional fields on the `UseCases` container. Rationale: they ARE use cases, and the `UseCases` container is the established pattern. Making them optional (`CreateProfile | None = None`, `ListProfiles | None = None`) preserves backward compatibility — existing code that constructs `UseCases` without them still works. The profile CLI methods check for None and print an error if somehow called without wiring.

  **Output formatting:**
  - `profile_create`: prints `Created profile '{name}' (db: {db_path})`
  - `profile_list`: prints profiles with `*` marking the default, matching the design spec format

- **Dependencies**: Unit 5, Unit 6.
- **Tests**: `tests/test_adapters/test_cli_commands.py` (extend) — output formatting for profile commands.

### Unit 9: Composition Root — Profile Resolution + Entry Point Changes

- **Layer**: composition root / entry points
- **Files**: `src/tw_guidance_computer/compose.py`, `src/tw_guidance_computer/cli.py`, `src/tw_guidance_computer/hud.py`
- **Description**:

  **compose.py** — Add a module-level function:
  ```python
  def resolve_db_path(profile_name: str | None, config_path: Path | None = None) -> Path:
  ```
  This function:
  1. Constructs `IniProfileStore(config_path or default_config_path())`
  2. Calls `store.ensure_config_exists()` — explicit, visible migration step
  3. Determines effective profile name: `profile_name or store.list_profiles().default_name`
  4. Calls `store.get_profile(effective_name)` to get the `Profile`
  5. Returns `Path(profile.db_path)` — the `str` → `Path` conversion happens here at the boundary

  Also add `default_config_path() -> Path` helper that returns `Path.home() / ".config" / "tw-guidance-computer" / "config.ini"`. This is infrastructure convention, correctly in the composition root.

  **Error handling in entry points** (`cli.py`, `hud.py`):
  - Wrap `resolve_db_path()` call in try/except
  - `ConfigError` → print `"Error: Failed to parse config: {details}"` to stderr, exit 1
  - `ProfileNotFoundError` → print `"Error: Profile '{name}' not found. Run 'tw profile list' to see available profiles."` to stderr, exit 1
  - These are user-facing errors with actionable messages

  **cli.py**:
  - Remove `--db` flag and `DEFAULT_DB_PATH` constant
  - Add `--profile / -p` global option (default: None, meaning "use configured default")
  - Add `tw profile create <name>` and `tw profile list` subcommands
  - For profile subcommands: construct `IniProfileStore` + use cases directly (they don't need `AppContext`)
  - For all other subcommands: call `resolve_db_path(args.profile)` then construct `AppContext` as before
  - If `--db` is passed (via argparse remainder or unknown args): print helpful error `"The --db flag has been removed. Use profiles instead: tw profile create <name>"`

  **hud.py**:
  - Remove `--db` flag
  - Add `--profile / -p` and `--create` flags
  - If `--create` and profile doesn't exist: construct `CreateProfile` use case, create the profile, print notice
  - If `--create` and profile exists: print notice that it already exists, continue
  - Call `resolve_db_path(args.profile)` then construct `AppContext` as before

- **Dependencies**: All previous units.
- **Tests**: `tests/test_adapters/test_ini_profile_store.py` covers the store integration. Entry point error handling tested via `tests/integration/test_profile_resolution.py` — verifies that `resolve_db_path` returns correct paths, handles missing config (auto-creates), and raises appropriate exceptions.

## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A (parallel) | Unit 1, Unit 2 | Independent domain additions, no shared files |
| B (after A) | Unit 3 | ProfileListing depends on Profile type from Unit 1 |
| C (after B) | Unit 4 | Port depends on Profile and ProfileListing types |
| D (after C, parallel) | Unit 5, Unit 6, Unit 7 | Use cases depend on port definition; adapter implements port. No shared files between them. |
| E (after D) | Unit 8 | Inbound adapter needs use cases from Unit 5/6 |
| F (after E) | Unit 9 | Composition root wires everything together |

## New Domain Types

- **`Profile`** — frozen dataclass. Fields: `name: str`, `db_path: str`. Validation in `__post_init__`: name must be 1-64 chars, match `^[a-z0-9-]+$`, not start or end with hyphen. Raises `ValidationError`. No `Path` type, no class methods for path generation.
- **`ProfileListing`** — frozen dataclass. Fields: `profiles: list[Profile]`, `default_name: str`. Derived property: `default_profile -> Profile | None`. Validates `default_name` is non-empty.

## New Ports

- **`ProfileStore`** — Protocol in `application/ports/profile_store.py`. Methods: `get_profile(name)`, `list_profiles()`, `save_profile(profile)`, `ensure_config_exists()`, `resolve_default_db_path(name)`. Abstracts config file I/O. Speaks domain types (`Profile`, `ProfileListing`). Raises domain exceptions (`ProfileNotFoundError`, `ProfileExistsError`, `ConfigError`).

## New Use Cases

- **`CreateProfile`** — Receives `ProfileStore` port. `execute(name: str) -> Profile`. Constructs `Profile` (triggers validation), calls `save_profile`. Raises `ProfileExistsError` if duplicate, `ValidationError` if bad name.
- **`ListProfiles`** — Receives `ProfileStore` port. `execute() -> ProfileListing`. Delegates to `store.list_profiles()`.

## Adapter Changes

- **`IniProfileStore` (new outbound)** — Implements `ProfileStore`. Uses `configparser` to read/write INI. `ensure_config_exists()` is an explicit method, not a constructor side effect. `resolve_default_db_path()` encodes the infrastructure convention (where DB files live, including the "default" → "game.db" special case).
- **`UseCases` container (modify)** — Add optional fields `create_profile: CreateProfile | None = None` and `list_profiles: ListProfiles | None = None`.
- **`CliAdapter` (modify inbound)** — Add `profile_create()` and `profile_list()` methods that use the new optional use cases from the container.
- **`cli.py` (modify entry point)** — Remove `--db`, add `--profile/-p`, add `profile` subcommand group. Error handling wraps `resolve_db_path()`.
- **`hud.py` (modify entry point)** — Remove `--db`, add `--profile/-p` and `--create`. Error handling wraps `resolve_db_path()`.
- **`compose.py` (modify)** — Add `resolve_db_path()` and `default_config_path()` helper functions. `AppContext` signature unchanged — still takes `db_path: Path`.

## Risk Notes

1. **Backward compatibility**: Users with scripts using `--db` will break. The design explicitly accepts this (UC#7). Entry points print a helpful error if `--db` is detected: "The --db flag has been removed. Use profiles instead: tw profile create <name>".
2. **Auto-migration race**: If both `tw` and `tw-hud` start simultaneously on first run, both may try to create the config file. Mitigation: `ensure_config_exists()` uses write-then-rename (atomic on POSIX) or accepts last-writer-wins (content is identical in both cases).
3. **Path expansion**: `~` in the INI file must be expanded when read. The adapter calls `os.path.expanduser()` on the `db` value before constructing the `Profile`. The `db_path` field on `Profile` always contains the expanded path.
4. **Config file permissions**: Create with `0o600` permissions from the start (future-proofing for sensitive config values).
5. **"default" → "game.db" special case**: Handled in `IniProfileStore.resolve_default_db_path()`. When name is `"default"`, returns path ending in `game.db`; otherwise `{name}.db`. This is tested explicitly in adapter tests.
