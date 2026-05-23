# Thread Safety Analysis — SQLite Connection Affinity

## Bug

```
StorageError: Database operation failed: SQLite objects created in a thread can only be used in that same thread.
```

The `intel_store = SqliteGameStateStore(db_path)` in `AppContext.__init__` calls `sqlite3.connect()` on the **main thread**. The `SyncIntelWorker.run()` executes on a **daemon thread** and calls `ExportIntel.execute()` → `intel_store.get_local_sectors()` → uses the main-thread connection → crash.

## Why the First Fix Failed

Creating a *separate* `SqliteGameStateStore` instance doesn't help because the issue isn't instance sharing — it's that `sqlite3.connect()` with `check_same_thread=True` (the default) binds the connection to the creating thread. A separate instance still creates its connection on the main thread.

## Analysis of Options

### Option 1: `check_same_thread=False` on the intel store

Add a constructor parameter to `SqliteGameStateStore`:

```python
def __init__(self, db_path: Path, *, check_same_thread: bool = True) -> None:
    self._conn = sqlite3.connect(str(db_path), isolation_level="DEFERRED", check_same_thread=check_same_thread)
```

**Pros:**
- Minimal change (1 parameter, 1 call site in compose.py)
- Architecturally clean — composition root decides thread policy
- WAL mode + separate connection = actually safe for concurrent access
- Main store keeps the safety check (catches real bugs)
- No change to use case layer, port definitions, or worker

**Cons:**
- Relies on the developer understanding that this store is used cross-thread
- The safety is implicit (WAL + separate connection) rather than enforced by the type system

**Risk assessment:** LOW. SQLite WAL mode is explicitly designed for concurrent readers/writers on separate connections. The `check_same_thread` flag is a Python-level safety check, not a SQLite-level one. With WAL + `busy_timeout=5000` + a dedicated connection, cross-thread use is well-defined behavior.

### Option 2: Lazy connection creation

Don't call `sqlite3.connect()` in `__init__`; create the connection on first use via a `@property`.

**Pros:**
- Connection is always created on the using thread
- No explicit cross-thread flag needed

**Cons:**
- Adds complexity to every method (property access or `_ensure_connected()` check)
- Schema initialization happens lazily — harder to reason about when errors surface
- Changes the store's contract: construction no longer guarantees a working database
- Breaks the existing test suite's assumptions about eager initialization
- Violates the principle that construction failures should fail fast

**Verdict:** Over-engineered for this problem. Introduces latent failure modes.

### Option 3: Create the store ON the worker thread

Have `SyncIntelWorker.run()` accept a `db_path` and construct its own `SqliteGameStateStore`, `ExportIntel`, `ImportIntel`, `PushIntel`, `PullIntel`.

**Pros:**
- Connection is guaranteed on the right thread
- No cross-thread flag needed

**Cons:**
- **Violates Composition Root codespec.** Construction logic moves from the composition root into the worker (an application-layer class). The worker would need to know about adapters (`SqliteGameStateStore`, `SftpTransport`) — breaking the dependency rule.
- Changes the worker's interface significantly
- Makes the worker harder to test (it constructs its own dependencies)

**Verdict:** Architecturally wrong. Rejected.

### Option 4: Worker builds its own stack in `run()`

Similar to Option 3 but the composition root passes a factory callable.

**Pros:**
- Connection on the right thread
- Factory keeps construction in the root (technically)

**Cons:**
- Adds a factory indirection that's only needed because of a Python-level thread check
- The factory would need to return a tuple of use cases — complex signature
- Over-engineered for the actual problem

**Verdict:** Unnecessary complexity for a well-understood, safe scenario.

## Recommendation: Option 1

Add `check_same_thread: bool = False` as a keyword argument to `SqliteGameStateStore.__init__`. Default remains `True` (safe). The composition root passes `check_same_thread=False` only for the intel store instance.

This is the correct fix because:

1. **The composition root decides thread policy** — it's the only place that knows which store goes to which thread. This is a wiring concern, not a domain concern.
2. **WAL mode makes it safe** — separate connections in WAL mode are the documented way to do concurrent SQLite access. The `check_same_thread` flag is a Python guardrail, not a SQLite requirement.
3. **Minimal blast radius** — one parameter added, one call site changed. No interface changes to ports, use cases, or the worker.
4. **Main store stays protected** — the parser's store keeps `check_same_thread=True`, so any accidental cross-thread use of the main store still crashes immediately (catching real bugs).

## Specific Code Changes

### 1. `src/tw_guidance_computer/adapters/outbound/sqlite_store.py`

```python
def __init__(self, db_path: Path, *, check_same_thread: bool = True) -> None:
    """Initialize the SQLite store.

    Args:
        db_path: Path to the SQLite database file.
        check_same_thread: If False, allow the connection to be used from
            a different thread than the one that created it. Only safe when
            this instance has its own connection (not shared) and WAL mode
            is enabled. Default True preserves SQLite's safety check.

    Raises:
        StorageError: If the database cannot be opened or initialized.
    """
    self._db_path = db_path
    try:
        self._conn = sqlite3.connect(
            str(db_path), isolation_level="DEFERRED", check_same_thread=check_same_thread
        )
        self._exec("PRAGMA journal_mode=WAL")
        self._exec("PRAGMA busy_timeout=5000")
        self._conn.executescript(_SCHEMA)
        self._run_migrations()
        self._commit()
    except sqlite3.Error as e:
        raise StorageError(f"Failed to initialize database: {e}") from e
```

### 2. `src/tw_guidance_computer/compose.py` (intel wiring section)

```python
if intel_config is not None and intel_identity is not None:
    intel_store = SqliteGameStateStore(db_path, check_same_thread=False)
    ...
```

Same change in `build_cli()`:
```python
if intel_config is not None and intel_identity is not None and db_path.exists():
    intel_store_instance = SqliteGameStateStore(db_path, check_same_thread=False)
    ...
```

### 3. No other changes needed

- Worker: unchanged
- Use cases (ExportIntel, ImportIntel, PushIntel, PullIntel): unchanged
- Port (IntelStore): unchanged
- Tests: unchanged (default `check_same_thread=True` preserves existing behavior)

## Why This Won't Break Tests

- The parameter has a default of `True` — all existing test code that constructs `SqliteGameStateStore(some_path)` continues to work identically.
- Tests that exercise the intel store directly run single-threaded, so `check_same_thread=True` is fine.
- The only call sites that pass `check_same_thread=False` are in the composition root, which tests don't exercise directly (they construct stores with defaults).
