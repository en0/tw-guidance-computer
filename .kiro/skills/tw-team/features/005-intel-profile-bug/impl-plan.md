# Implementation Plan: CLI intel commands ignore --profile flag

## Overview

`tw -p debug intel push/pull` always uses the default profile's intel config because `build_cli()` eagerly resolves intel with `_resolve_config(None, ...)`. The fix introduces an `intel_context_factory` — a callable that accepts `profile_name` and lazily constructs intel use cases, mirroring the existing `game_context_factory` pattern.

## Work Units

### Unit 1: Add intel_context_factory to CliAdapter

- **Layer**: adapters (inbound)
- **Files**: `src/tw_guidance_computer/adapters/inbound/cli_commands.py`
- **Description**:
  1. Define a new type alias: `IntelContextFactory = Callable[[str | None], tuple[PushIntel | None, PullIntel | None, IntelConfig | None, "IntelStore | None"]]`
  2. Add `intel_context_factory: IntelContextFactory | None = None` to `__init__` kwargs.
  3. Change `_dispatch_intel` to call the factory with `args.profile` when available, storing results on `self` before calling `intel_push`/`intel_pull`.
  4. When no factory is provided (direct injection in tests), fall back to the existing `self._push_intel` / `self._pull_intel` fields — preserving backward compat with all 412 tests.
- **Dependencies**: None.
- **Tests**: `tests/test_adapters/test_cli_intel.py` — add a test class `TestIntelProfileRouting` that constructs `CliAdapter` with a mock `intel_context_factory` and verifies it's called with the profile name from `-p`.

### Unit 2: Wire intel_context_factory in build_cli

- **Layer**: composition root
- **Files**: `src/tw_guidance_computer/compose.py`
- **Description**:
  1. Remove the eager intel resolution block (lines ~210-230 that call `_resolve_config(None, config_path)` for intel).
  2. Define a local `intel_context_factory` closure that accepts `profile_name: str | None`, calls `_resolve_config(profile_name, config_path)`, constructs `PushIntel`/`PullIntel`/`SqliteGameStateStore` if intel is configured, and returns the tuple.
  3. Pass `intel_context_factory` to `CliAdapter` instead of `push_intel`/`pull_intel`/`intel_config`/`intel_store`.
  4. Remove `push_intel`, `pull_intel`, `intel_config`, `intel_store` kwargs from the `build_cli` call (they become unused — the factory provides them).
- **Dependencies**: Unit 1 (CliAdapter must accept the factory).
- **Tests**: Existing integration tests via `build_cli()` should still pass. Add one test in `test_cli_intel.py` that verifies `build_cli` passes a factory (or test via the profile-routing test from Unit 1).

## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A | Unit 1 | Adapter change, defines the interface |
| B (after A) | Unit 2 | Composition root wires the factory |

## New Domain Types

None.

## New Ports

None.

## New Use Cases

None.

## Adapter Changes

### CliAdapter (`cli_commands.py`)

**New constructor parameter:**
```python
intel_context_factory: IntelContextFactory | None = None
```

**Changed `_dispatch_intel`:**
```python
def _dispatch_intel(self, args: argparse.Namespace) -> None:
    # Resolve intel for the requested profile
    if self._intel_context_factory is not None:
        push, pull, config, store = self._intel_context_factory(args.profile)
        self._push_intel = push
        self._pull_intel = pull
        self._intel_config = config
        self._intel_store = store

    match args.intel_command:
        case "push":
            self.intel_push()
        case "pull":
            self.intel_pull()
        case _:
            print("Usage: tw intel {push|pull}", file=sys.stderr)
            sys.exit(1)
```

This is the minimal change — when a factory exists, it resolves intel for the given profile before dispatching. When no factory exists (test injection), the existing fields are used as-is.

### compose.py (`build_cli`)

**Replace eager resolution with factory:**
```python
def build_cli(config_path: Path | None = None) -> CliAdapter:
    create, list_profiles = build_profile_use_cases(config_path)

    def intel_context_factory(
        profile_name: str | None,
    ) -> tuple[PushIntel | None, PullIntel | None, IntelConfig | None, SqliteGameStateStore | None]:
        db_path, _, _, intel_config, intel_identity = _resolve_config(profile_name, config_path)
        if intel_config is None or intel_identity is None or not db_path.exists():
            return None, None, None, None
        store = SqliteGameStateStore(db_path, check_same_thread=False)
        transport = SftpTransport(intel_config)
        export_intel = ExportIntel(store)
        import_intel = ImportIntel(store)
        push = PushIntel(export_intel, transport, intel_identity)
        pull = PullIntel(import_intel, transport, intel_identity, intel_config.max_file_size)
        return push, pull, intel_config, store

    def game_context_factory(
        profile_name: str | None,
    ) -> tuple[UseCases, Callable[[], None]]:
        ctx = AppContext(
            profile_name=profile_name,
            config_path=config_path,
            require_existing_db=True,
        )
        return ctx.use_cases, ctx.close

    return CliAdapter(
        create_profile=create,
        list_profiles=list_profiles,
        game_context_factory=game_context_factory,
        intel_context_factory=intel_context_factory,
    )
```

## Risk Notes

1. **Resource cleanup**: The factory creates a `SqliteGameStateStore` per invocation. For CLI one-shot commands this is fine — the process exits immediately after. No leak risk.

2. **Backward compat**: Existing tests inject `push_intel`/`pull_intel` directly without a factory. The fallback path (no factory → use injected fields) preserves all 412 tests unchanged.

3. **Type alias placement**: `IntelContextFactory` goes in `cli_commands.py` alongside `GameContextFactory` — same pattern, same location.
