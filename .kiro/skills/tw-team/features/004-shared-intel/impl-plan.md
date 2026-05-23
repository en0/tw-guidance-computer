# Implementation Plan: Shared Sector Intelligence

## Overview

Add SFTP-based shared intel sync to the guidance computer. Players push local sector/port/warp/planet discoveries to a shared server and pull other players' discoveries into their local DB. The HUD auto-syncs in the background; CLI provides manual push/pull commands. A Docker container provides the SFTP-only intel server.

## Architecture Decisions

### 1. `updated_at` Is an Adapter Concern (Addresses Design Review Issue #2)

Domain models (`Sector`, `Port`, `WarpConnection`, `Planet`) remain unchanged — no timestamp fields added. The `updated_at` column is managed entirely by the SQLite adapter:

- **Local writes** (parser path): The adapter sets `updated_at = time.time()` on every upsert. The parser and use cases are unaware of timestamps.
- **Import writes** (intel path): A new port method `import_intel(...)` accepts explicit timestamps from the imported CSV data. The adapter uses these timestamps for freshness comparison.

This keeps timestamps as a storage/sync concern, not a domain concept. The domain models stay pure.

### 2. `source` Column Is an Adapter Concern (Addresses Design Review Issue #3)

Same principle. The `source TEXT` column is added to SQLite tables but never surfaces in domain models:

- **Local writes**: Adapter sets `source = NULL` implicitly (existing upsert methods unchanged).
- **Import writes**: The new `import_intel(...)` method sets `source = <keyhash>`.
- **Export reads**: New `get_local_*()` methods filter `WHERE source IS NULL`.

Schema migration: `ALTER TABLE ADD COLUMN` with defaults handles existing databases. SQLite allows adding columns with defaults without rewriting the table.

### 3. New Port: `IntelStore` (Separate from GameStateStore)

Intel-specific bulk operations get their own port rather than bloating `GameStateReader`/`GameStateWriter`:

- `IntelStore` — Protocol with methods for bulk export (local-only data) and bulk import (with timestamps and source tracking).
- `SqliteGameStateStore` implements both `GameStateStore` and `IntelStore`.

This keeps the existing ports focused and avoids changing signatures of methods used by the parser.

### 4. New Port: `IntelTransport`

Abstracts SFTP operations so the use cases don't depend on paramiko or subprocess:

- `upload(local_path: Path, remote_name: str) -> None`
- `download(remote_name: str, local_path: Path) -> None`
- `list_files() -> list[RemoteFile]`

Implementation uses `subprocess` calling the system `sftp` binary (no new dependency, available on all target systems, simpler than paramiko).

### 5. Background Sync Worker (Thread)

The HUD sync worker runs in a `threading.Thread`. Communication with the render loop is via a simple shared state object (frozen dataclass replaced atomically). The worker:

- Pulls on startup
- Pushes + pulls on interval
- Pushes on shutdown (triggered by main thread setting a flag)

Thread safety: The worker writes to SQLite (WAL mode handles concurrent access). The render loop reads a `SyncStatus` dataclass that the worker replaces atomically (Python's GIL makes single-reference assignment atomic).

### 6. Docker Container Trust Model (Addresses Design Review Issue #4)

Acknowledged: All authenticated players share a single SFTP user chrooted to `/data/`. Any player can read/write/delete any file. This is acceptable because:

- Corp mates are trusted
- The client only writes to its own keyhash file (enforced client-side)
- Server-side isolation would require per-key ForceCommand scripting (complexity not justified for a game tool)

The README documents this trust assumption explicitly.

### 7. CSV File Format (Addresses Design Review Issue #8)

Single file per player containing all record types, sectioned with type headers:

```
#TYPE:sectors
id,region,explored,updated_at
616,uncharted space,1,1716400000.0
#TYPE:ports
sector_id,name,port_class,port_type,commodities_json,updated_at
616,Trader Vic's,6,SBS,"[...]",1716400000.0
#TYPE:warps
from_sector,to_sector,explored,updated_at
616,544,1,1716400000.0
#TYPE:planets
sector_id,name,planet_class,updated_at
616,es,M,1716400000.0
#SHA256:<hash of all preceding content>
```

Uses Python's `csv` module (stdlib). Port names with commas are handled by standard CSV quoting.


## Work Units

### Unit 1: Domain — Intel Value Objects and Exceptions

- **Layer**: domain
- **Files**: `src/tw_guidance_computer/domain/models/intel.py`, update `domain/models/__init__.py`, update `domain/exceptions.py`
- **Description**:
  New value objects in `domain/models/intel.py`:
  - `IntelConfig` — frozen dataclass. Fields: `host: str`, `key_path: str`, `port: int = 22`, `sync_interval: int = 300`, `sync_budget: int = 30`, `max_file_size: int = 10485760`. Validates: `host` non-empty, `port` 1–65535, `sync_budget < sync_interval`, `max_file_size > 0`.
  - `RemoteFile` — frozen dataclass. Fields: `name: str`, `size: int`. Validates: `name` non-empty, `size >= 0`.
  - `IntelMergeResult` — frozen dataclass. Fields: `sectors_added: int = 0`, `ports_added: int = 0`, `ports_updated: int = 0`, `warps_added: int = 0`, `planets_added: int = 0`. Derived property `total -> int`.
  - `SyncStatus` — frozen dataclass. Fields: `last_error: str | None = None`, `shutdown_status: str | None = None`. Used for HUD render loop communication.

  New exceptions in `domain/exceptions.py`:
  - `IntelError(GuidanceError)` — base for all intel errors.
  - `IntelConnectError(IntelError)` — connection/auth failures (E10, E24, E31).
  - `IntelTransferError(IntelError)` — read/write failures (E38, E45).
  - `IntelDataError(IntelError)` — corrupt/invalid data (E17, E52, E59).
  - `IntelKeyError(IntelError)` — key file inaccessible (E66).

  Re-export all new types from `domain/models/__init__.py`.
- **Dependencies**: None.
- **Tests**: `tests/test_domain/test_intel.py` — construction, validation failures, derived properties, frozen.

### Unit 2: Port — IntelStore Protocol

- **Layer**: application/ports
- **Files**: `src/tw_guidance_computer/application/ports/intel_store.py`
- **Description**: New Protocol defining bulk export/import operations for intel sync:
  ```python
  class IntelStore(Protocol):
      def get_local_sectors(self) -> list[Sector]: ...
      def get_local_ports(self) -> list[Port]: ...
      def get_local_warps(self) -> list[WarpConnection]: ...
      def get_local_planets(self) -> list[Planet]: ...
      def get_sector_updated_at(self, sector_id: int) -> float: ...
      def get_port_updated_at(self, sector_id: int) -> float: ...
      def import_sectors(self, sectors: list[tuple[Sector, float]], source: str) -> int: ...
      def import_ports(self, ports: list[tuple[Port, float]], source: str) -> int: ...
      def import_warps(self, warps: list[tuple[WarpConnection, float]], source: str) -> int: ...
      def import_planets(self, planets: list[tuple[Planet, float]], source: str) -> int: ...
  ```
  - `get_local_*()` methods return only records where `source IS NULL`.
  - `import_*()` methods accept `(domain_object, updated_at)` tuples and a source keyhash. Return count of records actually inserted/updated.
  - `import_sectors` uses "explored beats unexplored" merge strategy.
  - `import_ports` uses "freshest `updated_at` wins" merge strategy.
  - `import_warps` uses additive (INSERT OR IGNORE) strategy.
  - `import_planets` uses additive (INSERT OR IGNORE) strategy.
  - All methods raise `StorageError` on failure.
- **Dependencies**: None (Protocol definition only).
- **Tests**: Tested via adapter implementation (Unit 5).

### Unit 3: Port — IntelTransport Protocol

- **Layer**: application/ports
- **Files**: `src/tw_guidance_computer/application/ports/intel_transport.py`
- **Description**: New Protocol abstracting SFTP file operations:
  ```python
  class IntelTransport(Protocol):
      def connect(self) -> None: ...
      def disconnect(self) -> None: ...
      def upload(self, local_path: Path, remote_name: str) -> None: ...
      def download(self, remote_name: str, local_path: Path) -> None: ...
      def list_files(self) -> list[RemoteFile]: ...
  ```
  - `connect()` raises `IntelConnectError` on failure.
  - `upload()` raises `IntelTransferError` on failure.
  - `download()` raises `IntelTransferError` on failure. Respects max file size (checked via `list_files` size before download).
  - `list_files()` raises `IntelTransferError` on failure.
  - `disconnect()` never raises (best-effort cleanup).
- **Dependencies**: Unit 1 (uses `RemoteFile`, `IntelConnectError`, `IntelTransferError`).
- **Tests**: Tested via adapter implementation (Unit 6).

### Unit 4: Domain — Intel CSV Serialization

- **Layer**: domain (pure computation, no I/O)
- **Files**: `src/tw_guidance_computer/domain/intel_csv.py`
- **Description**: Pure functions for serializing/deserializing intel data to/from CSV format. No file I/O — operates on strings.
  - `serialize_intel(sectors, ports, warps, planets) -> str` — produces the sectioned CSV string with SHA-256 checksum trailer.
  - `deserialize_intel(content: str) -> tuple[list[tuple[Sector, float]], list[tuple[Port, float]], list[tuple[WarpConnection, float]], list[tuple[Planet, float]]]` — parses sectioned CSV, validates checksum. Raises `IntelDataError` on checksum mismatch or parse failure.
  - Uses `csv` module (stdlib) for proper quoting of port names containing commas.
  - `compute_identity(pub_key_path: Path) -> str` — reads the `.pub` file, computes SHA-256 hex hash. Raises `IntelKeyError` if file not found.

  Note: `compute_identity` does file I/O (reads pubkey). This is acceptable as a thin utility — the alternative (a port for reading a single file) is over-engineering. It lives in domain because the identity derivation rule (SHA-256 of pubkey content) is a domain concept.

  **Correction**: Move `compute_identity` to a separate utility in adapters since it does I/O. The domain module contains only the pure serialization functions.
- **Dependencies**: Unit 1 (uses domain types and `IntelDataError`).
- **Tests**: `tests/test_domain/test_intel_csv.py` — round-trip serialization, checksum validation, corrupt data rejected, port names with commas handled, empty data sets.


### Unit 5: Adapter — SQLite IntelStore Implementation + Schema Migration

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/sqlite_store.py`
- **Description**: Extend `SqliteGameStateStore` to implement `IntelStore`. Changes:

  **Schema migration** (in `__init__`):
  After running `_SCHEMA`, execute migration SQL:
  ```sql
  -- Add source and updated_at to existing tables (idempotent)
  ALTER TABLE sectors ADD COLUMN source TEXT DEFAULT NULL;
  ALTER TABLE sectors ADD COLUMN updated_at REAL DEFAULT 0.0;
  ALTER TABLE ports ADD COLUMN source TEXT DEFAULT NULL;
  ALTER TABLE ports ADD COLUMN updated_at REAL DEFAULT 0.0;
  ALTER TABLE warps ADD COLUMN source TEXT DEFAULT NULL;
  ALTER TABLE warps ADD COLUMN updated_at REAL DEFAULT 0.0;
  ALTER TABLE planets ADD COLUMN source TEXT DEFAULT NULL;
  ALTER TABLE planets ADD COLUMN updated_at REAL DEFAULT 0.0;
  ```
  Wrap each `ALTER TABLE` in try/except to handle "duplicate column" error (idempotent migration).

  **Modify existing upsert methods**: Add `updated_at = time.time()` to INSERT values. Keep `source` as NULL (implicit default). The ON CONFLICT clauses remain unchanged — local writes always overwrite local data.

  **New methods** (implementing `IntelStore`):
  - `get_local_sectors()`: `SELECT ... FROM sectors WHERE source IS NULL`
  - `get_local_ports()`: `SELECT ... FROM ports WHERE source IS NULL`
  - `get_local_warps()`: `SELECT ... FROM warps WHERE source IS NULL`
  - `get_local_planets()`: `SELECT ... FROM planets WHERE source IS NULL`
  - `get_sector_updated_at(sector_id)`: `SELECT updated_at FROM sectors WHERE id = ?`
  - `get_port_updated_at(sector_id)`: `SELECT updated_at FROM ports WHERE sector_id = ?`
  - `import_sectors(sectors, source)`: For each sector, INSERT OR UPDATE with "explored beats unexplored" logic. Sets `source` and `updated_at` from the provided values.
  - `import_ports(ports, source)`: For each port, compare `updated_at` — only update if incoming is fresher. Sets `source`.
  - `import_warps(warps, source)`: `INSERT OR IGNORE` with `source` set.
  - `import_planets(planets, source)`: `INSERT OR IGNORE` with `source` set.

  **Performance**: Import methods use `executemany` where possible and commit once per batch (not per row).

- **Dependencies**: Unit 2 (IntelStore Protocol).
- **Tests**: `tests/test_adapters/test_sqlite_intel.py` — migration idempotent, local-only export filters correctly, import respects freshness, import respects explored-beats-unexplored, additive warps/planets, source column set correctly, existing upserts still work (regression).

### Unit 6: Adapter — SFTP Transport (subprocess)

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/sftp_transport.py`
- **Description**: Implements `IntelTransport` using subprocess calls to the system `sftp` binary. No new Python dependencies.

  Constructor: `SftpTransport(config: IntelConfig)`

  **Implementation approach**: Uses `subprocess.run()` with batch mode (`-b` flag) to execute SFTP commands non-interactively. SSH key specified via `-i` flag. Port via `-P` flag.

  Methods:
  - `connect()`: Runs `sftp -i <key> -P <port> -b /dev/null user@host` to verify connectivity. Raises `IntelConnectError` on non-zero exit (parses stderr for auth vs. connection errors).
  - `upload(local_path, remote_name)`: Writes a batch file with `put <local> <remote>`, runs sftp. Raises `IntelTransferError` on failure.
  - `download(remote_name, local_path)`: Writes a batch file with `get <remote> <local>`, runs sftp. Raises `IntelTransferError` on failure.
  - `list_files()`: Runs `ls -l` via batch, parses output into `RemoteFile` objects. Raises `IntelTransferError` on failure.
  - `disconnect()`: No-op (subprocess connections are stateless).

  **SFTP user**: Hardcoded as `intel` (the Docker container's single user). Could be made configurable later.

  **Error code mapping**:
  - Connection refused / timeout → `IntelConnectError` (E24)
  - Permission denied → `IntelConnectError` (E31)
  - Upload failure → `IntelTransferError` (E38)
  - Download failure → `IntelTransferError` (E45)

- **Dependencies**: Unit 1 (IntelConfig, RemoteFile, exceptions), Unit 3 (IntelTransport Protocol).
- **Tests**: `tests/test_adapters/test_sftp_transport.py` — mock subprocess.run, verify correct command construction, error translation for various exit codes and stderr patterns.

### Unit 7: Application — ExportIntel and ImportIntel Use Cases

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/export_intel.py`, `src/tw_guidance_computer/application/import_intel.py`
- **Description**:

  **ExportIntel** (`@final`):
  - Constructor: `__init__(self, store: IntelStore)`
  - `execute() -> str` — Reads all local data via `get_local_*()` methods, serializes to CSV string using `serialize_intel()`. Returns the CSV content. Raises `IntelDataError` if serialization fails.
  - Returns the serialized string (caller decides what to do with it — write to file for upload).

  **ImportIntel** (`@final`):
  - Constructor: `__init__(self, store: IntelStore)`
  - `execute(content: str, source: str) -> IntelMergeResult` — Deserializes CSV content via `deserialize_intel()`, calls `import_*()` methods on the store. Returns merge statistics. Raises `IntelDataError` on corrupt input.

  These are thin orchestration — the real logic is in the CSV serialization (domain) and the store's merge strategies (adapter).

- **Dependencies**: Unit 1 (value objects), Unit 2 (IntelStore port), Unit 4 (serialization functions).
- **Tests**: `tests/test_application/test_export_intel.py`, `tests/test_application/test_import_intel.py` — mock IntelStore, verify correct delegation, verify merge result aggregation.


### Unit 8: Application — PushIntel and PullIntel Use Cases

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/push_intel.py`, `src/tw_guidance_computer/application/pull_intel.py`
- **Description**:

  **PushIntel** (`@final`):
  - Constructor: `__init__(self, export: ExportIntel, transport: IntelTransport, identity: str)`
  - `execute() -> int` — Calls `export.execute()` to get CSV content. Writes to a temp file. Calls `transport.upload(temp_file, self._identity)`. Returns total record count. Cleans up temp file.
  - Raises `IntelTransferError` on upload failure, `IntelDataError` on export failure.

  **PullIntel** (`@final`):
  - Constructor: `__init__(self, import_intel: ImportIntel, transport: IntelTransport, identity: str, max_file_size: int)`
  - `execute(budget_seconds: float | None = None, offset: int = 0) -> IntelMergeResult` — Lists remote files, excludes own identity file, downloads and imports each file. Respects time budget (stops pulling new files when budget expires). Skips files exceeding `max_file_size`. Accumulates `IntelMergeResult` across all sources.
  - On per-file corruption (`IntelDataError`): logs warning, skips file, continues with next. Does NOT abort the entire pull.
  - Returns aggregate `IntelMergeResult`.
  - `offset` parameter supports the rotating offset algorithm for background sync.

- **Dependencies**: Unit 1, Unit 3 (IntelTransport), Unit 7 (ExportIntel, ImportIntel).
- **Tests**: `tests/test_application/test_push_intel.py`, `tests/test_application/test_pull_intel.py` — mock transport and export/import, verify file skipping on corruption, budget enforcement, offset rotation, own-file exclusion.

### Unit 9: Application — SyncIntelWorker (Background Thread Logic)

- **Layer**: application
- **Files**: `src/tw_guidance_computer/application/sync_intel_worker.py`
- **Description**: Encapsulates the background sync algorithm. NOT a thread itself — it's a use case that the HUD adapter runs in a thread.

  **SyncIntelWorker** (`@final`):
  - Constructor: `__init__(self, push: PushIntel, pull: PullIntel, config: IntelConfig)`
  - Fields: `_status: SyncStatus` (atomically replaced), `_sync_counter: int`, `_stop_requested: bool`, `_shutdown_requested: bool`
  - `run() -> None` — Main loop: pull on startup, then loop (push+pull on interval) until stopped. Updates `_status` on each cycle.
  - `request_shutdown() -> None` — Sets flag, triggers final push, updates `_status.shutdown_status` with progress.
  - `request_stop() -> None` — Force stop (second ctrl+c).
  - `get_status() -> SyncStatus` — Returns current status (thread-safe read).

  **Error handling**: All `IntelError` exceptions are caught within the worker. On failure, `_status.last_error` is set to the error code string (e.g., "E24"). On next successful cycle, `last_error` is cleared.

  **Error code mapping**:
  - `IntelConnectError` → "E24" (connect) or "E31" (auth, detected by message)
  - `IntelTransferError` → "E38" (during push) or "E45" (during pull)
  - `IntelDataError` → "E17" (during export) or "E52" (during import)
  - `IntelKeyError` → "E66"

  **Shutdown sequence**:
  1. `request_shutdown()` called by HUD
  2. Worker sets `shutdown_status = "Exporting sectors..."`
  3. Runs push (updating status as it progresses)
  4. Sets `shutdown_status = "Done."` or `"Push failed: <reason>"`
  5. Worker exits

- **Dependencies**: Unit 1 (IntelConfig, SyncStatus, exceptions), Unit 8 (PushIntel, PullIntel).
- **Tests**: `tests/test_application/test_sync_intel_worker.py` — mock push/pull, verify startup pull, interval push+pull, shutdown push, error status propagation, stop behavior.

### Unit 10: Adapter — Intel Identity Utility

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/outbound/intel_identity.py`
- **Description**: Utility function for computing player identity from SSH public key:
  ```python
  def compute_intel_identity(key_path: str) -> str:
  ```
  - Reads `key_path + ".pub"`, computes SHA-256 hex hash of file content.
  - Raises `IntelKeyError` if `.pub` file doesn't exist.
  - Lives in adapters because it does file I/O.

  Also: startup validation function:
  ```python
  def validate_intel_config(config: IntelConfig) -> None:
  ```
  - Checks `key_path` file exists on disk.
  - Checks `key_path + ".pub"` exists on disk.
  - Raises `IntelKeyError` with descriptive message if either is missing.

- **Dependencies**: Unit 1 (IntelConfig, IntelKeyError).
- **Tests**: `tests/test_adapters/test_intel_identity.py` — computes correct hash, raises on missing pubkey, raises on missing private key.


### Unit 11: Adapter — HUD Intel Integration (Error Indicator + Shutdown Modal)

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/inbound/tui.py`, `src/tw_guidance_computer/adapters/inbound/sync_modal.py`
- **Description**:

  **New file `sync_modal.py`**: Pure helper (same pattern as `alert_overlay.py`):
  ```python
  def format_sync_modal(status: str | None) -> list[str]:
  ```
  Returns content lines for the shutdown modal box. Returns empty list if status is None.

  **Changes to `tui.py`**:

  1. **New constructor parameters**: Accept optional `sync_worker: SyncIntelWorker | None = None` (None when intel not configured).

  2. **Background thread startup**: In `_main_loop`, before the render loop, if `sync_worker` is not None, start it in a `threading.Thread(target=sync_worker.run, daemon=True)`.

  3. **Error indicator in header** (`_render_header`):
     - After rendering Credits, check `sync_worker.get_status().last_error`
     - If error present and terminal wide enough (≥90 cols): append `  │  ! Intel E##` in red bold reverse
     - If error present and terminal 90 > width (but fits compact): append `  │  ! E##`
     - Uses curses color pair 4 with `A_BOLD | A_REVERSE | A_BLINK`

  4. **Shutdown modal** (replaces immediate exit on `q`):
     - When `q` pressed or first SIGINT: set `self._shutting_down = True`, call `sync_worker.request_shutdown()`
     - Render loop continues but renders the shutdown modal overlay instead of normal content
     - Modal uses `format_sync_modal()` for content, rendered with cyan border (same box pattern as alert overlay)
     - When `shutdown_status == "Done."`: sleep 500ms, exit
     - When `shutdown_status` starts with "Push failed:": sleep 1500ms, exit
     - Second SIGINT while shutting down: call `sync_worker.request_stop()`, exit immediately

  5. **Z-order**: `if shutting_down: render_sync_modal() elif alert_active: render_alert_overlay()`

  6. **When intel not configured**: No worker started, `q` exits immediately (current behavior), no indicator rendered.

  7. **SIGINT handling**: Register `signal.signal(signal.SIGINT, handler)` in `_main_loop`. Handler sets `_sigint_count += 1`. First SIGINT triggers shutdown. Second SIGINT forces exit.

- **Dependencies**: Unit 1 (SyncStatus), Unit 9 (SyncIntelWorker).
- **Tests**: `tests/test_adapters/test_sync_modal.py` — format_sync_modal output for various states. HUD integration tested manually (curses is hard to unit test).

### Unit 12: Adapter — CLI Intel Commands

- **Layer**: adapters
- **Files**: `src/tw_guidance_computer/adapters/inbound/cli_commands.py`
- **Description**: Add `intel_push()` and `intel_pull()` methods to `CliAdapter`. Add `intel` subcommand group with `push` and `pull` subcommands.

  **`intel_push()`**:
  - Reads local counts from IntelStore (for progress display)
  - Calls `push_intel.execute()`
  - Prints: "Exporting N sectors, N ports, N warps, N planets..."
  - Prints: "Uploading to host:port..."
  - Prints: "Done. Pushed N records."
  - On error: prints error code and message to stderr, exits 1

  **`intel_pull()`**:
  - Calls `pull_intel.execute()` (no budget for CLI — runs to completion)
  - Prints per-source download progress
  - Prints merge summary: "+N sectors, +N ports, N ports updated (fresher), +N warps"
  - On per-file corruption: prints warning, continues
  - On connect error: prints error to stderr, exits 1

  **Config validation**: Before any operation, validates intel config (key exists, pubkey exists). Prints actionable error messages on failure.

- **Dependencies**: Unit 1, Unit 8 (PushIntel, PullIntel), Unit 10 (identity/validation).
- **Tests**: `tests/test_adapters/test_cli_intel.py` — output formatting for push/pull success, error output for failures, config validation errors.

### Unit 13: Composition Root — Intel Wiring

- **Layer**: composition root
- **Files**: `src/tw_guidance_computer/compose.py`, `src/tw_guidance_computer/application/use_cases.py`
- **Description**:

  **Config resolution** (extend `_resolve_config`):
  - Read `intel_host`, `intel_key`, `intel_port`, `intel_sync_interval`, `intel_sync_budget`, `intel_max_file_size` from profile config via `get_config_value()`.
  - If `intel_host` is set: construct `IntelConfig`, validate key files, compute identity.
  - If `intel_host` is not set: intel is None (disabled).
  - Return `IntelConfig | None` alongside existing return values.

  **AppContext changes**:
  - New field: `intel_config: IntelConfig | None`
  - New field: `intel_identity: str | None`
  - If intel configured: construct `SftpTransport`, `ExportIntel`, `ImportIntel`, `PushIntel`, `PullIntel`, `SyncIntelWorker`
  - Expose `sync_worker: SyncIntelWorker | None` for HUD to use
  - Expose `push_intel: PushIntel | None` and `pull_intel: PullIntel | None` for CLI

  **HUD factory changes** (`build_hud`):
  - Pass `sync_worker` to `HudDisplay` constructor (or None if intel disabled)

  **CLI factory changes** (`build_cli`):
  - Pass `push_intel` and `pull_intel` to `CliAdapter` (or None if intel disabled)
  - CLI intel commands check for None and print "Intel not configured" error

  **UseCases container**: NOT modified — intel use cases are passed separately to the adapters that need them (HUD gets the worker, CLI gets push/pull directly). This avoids making all existing tests aware of intel.

- **Dependencies**: All previous units.
- **Tests**: `tests/integration/test_intel_wiring.py` — verify AppContext constructs intel components when config present, skips when absent, startup validation errors propagate.

### Unit 14: Docker Container + README

- **Layer**: infrastructure (not Python code)
- **Files**: `docker/intel-server/Dockerfile`, `docker/intel-server/sshd_config`, `docker/intel-server/entrypoint.sh`, `README.md` (update)
- **Description**:

  **Dockerfile**:
  ```dockerfile
  FROM alpine:3.20
  RUN apk add --no-cache openssh-server && \
      adduser -D -s /sbin/nologin intel && \
      mkdir -p /data && chown intel:intel /data
  COPY sshd_config /etc/ssh/sshd_config
  COPY entrypoint.sh /entrypoint.sh
  RUN chmod +x /entrypoint.sh
  EXPOSE 22
  ENTRYPOINT ["/entrypoint.sh"]
  ```

  **sshd_config**:
  - `ForceCommand internal-sftp`
  - `ChrootDirectory /data`
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `AuthorizedKeysFile /etc/tw-intel/keys`
  - `Subsystem sftp internal-sftp`

  **entrypoint.sh**:
  - Generate host keys if not present
  - Start sshd in foreground

  **README update**:
  - Section: "Shared Intel Server"
  - Subsections: Running the container, Adding player keys, Client configuration, Data layout, Maintenance commands, Trust model acknowledgment
  - Docker run command: `docker run -d -p 2222:22 -v ./authorized_keys:/etc/tw-intel/keys:ro -v ./data:/data tw-guidance-computer/intel-server`

- **Dependencies**: None (can be built in parallel with everything).
- **Tests**: Manual verification (build container, test SFTP access, verify shell rejected).


## Parallel Execution Plan

| Group | Units | Rationale |
|-------|-------|-----------|
| A (parallel) | Unit 1, Unit 14 | Domain types + Docker container. Completely independent. |
| B (after A, parallel) | Unit 2, Unit 3, Unit 4, Unit 10 | Port definitions + CSV serialization + identity utility. All depend on Unit 1 types but not on each other. Different files. |
| C (after B, parallel) | Unit 5, Unit 6 | SQLite IntelStore implementation + SFTP transport. Both implement ports from Group B. Different files. |
| D (after C, parallel) | Unit 7 | ExportIntel + ImportIntel use cases. Need both ports implemented for testing. |
| E (after D) | Unit 8 | PushIntel + PullIntel. Need Unit 7 use cases. |
| F (after E) | Unit 9 | SyncIntelWorker. Needs push/pull from Unit 8. |
| G (after F, parallel) | Unit 11, Unit 12 | HUD integration + CLI commands. Both need the worker/push/pull but modify different files. |
| H (after G) | Unit 13 | Composition root wiring. Touches compose.py, connects everything. |

## New Domain Types

- **`IntelConfig`** — frozen dataclass. Connection and sync configuration. Validates host non-empty, port range, budget < interval.
- **`RemoteFile`** — frozen dataclass. SFTP file listing entry. Fields: `name`, `size`.
- **`IntelMergeResult`** — frozen dataclass. Import statistics. Derived property: `total`.
- **`SyncStatus`** — frozen dataclass. Worker state for HUD communication. Fields: `last_error`, `shutdown_status`.

## New Exceptions

- **`IntelError`** — base for all intel failures.
- **`IntelConnectError`** — network/auth failures.
- **`IntelTransferError`** — SFTP read/write failures.
- **`IntelDataError`** — corrupt or invalid data.
- **`IntelKeyError`** — SSH key file inaccessible.

## New Ports

- **`IntelStore`** — Bulk export (local-only) and import (with timestamps/source) operations. Implemented by `SqliteGameStateStore`.
- **`IntelTransport`** — SFTP file operations (connect, upload, download, list). Implemented by `SftpTransport`.

## New Use Cases

- **`ExportIntel`** — Reads local data from IntelStore, serializes to CSV string.
- **`ImportIntel`** — Deserializes CSV, imports into IntelStore with merge strategies.
- **`PushIntel`** — Orchestrates export + upload via transport.
- **`PullIntel`** — Orchestrates download + import for all remote sources. Handles per-file errors gracefully.
- **`SyncIntelWorker`** — Background sync algorithm (startup pull, interval push+pull, shutdown push). Manages status for HUD.

## Adapter Changes

- **`SqliteGameStateStore`** (modify): Schema migration (add `source`, `updated_at` columns). Implement `IntelStore` protocol. Modify existing upserts to set `updated_at = time.time()`.
- **`SftpTransport`** (new outbound): Subprocess-based SFTP client. Implements `IntelTransport`.
- **`intel_identity.py`** (new outbound): Computes player identity hash, validates key files.
- **`HudDisplay`** (modify inbound): Accept optional sync worker. Start background thread. Render error indicator in header. Render shutdown modal. Handle SIGINT for graceful/force shutdown.
- **`sync_modal.py`** (new inbound helper): Pure function for shutdown modal content.
- **`CliAdapter`** (modify inbound): Add `intel push` and `intel pull` subcommands.
- **`IniProfileStore`** (no changes): Already supports reading arbitrary config keys via `get_config_value()`.

## Composition Root Changes

- **`_resolve_config()`**: Extended to read `intel_*` config keys and construct `IntelConfig | None`.
- **`AppContext`**: Constructs intel components when configured. Exposes `sync_worker` and `push_intel`/`pull_intel`.
- **`build_hud()`**: Passes sync worker to HUD.
- **`build_cli()`**: Passes push/pull use cases to CLI adapter.

## Risk Notes

1. **Schema migration on existing databases**: `ALTER TABLE ADD COLUMN` is safe in SQLite — it doesn't rewrite the table. Existing rows get `source = NULL` and `updated_at = 0.0`. The `0.0` timestamp means existing data will be "older" than any freshly-pushed data from other players, which is correct behavior (their fresh observations should win over our stale pre-timestamp data).

2. **Thread safety**: The sync worker writes to SQLite via the same `SqliteGameStateStore` instance the render loop reads from. WAL mode handles this — concurrent readers don't block writers and vice versa. The `SyncStatus` object is replaced atomically (single reference assignment under GIL).

3. **subprocess SFTP vs. paramiko**: Using subprocess avoids adding a dependency (paramiko + cryptography is heavy). Tradeoff: requires `sftp` binary on the system. This is available on all Linux/macOS systems and WSL. If a user doesn't have it, they get a clear `IntelConnectError` (E10) at startup.

4. **Time budget enforcement**: The pull use case checks elapsed time between file downloads. If a single large file download exceeds the budget, it completes (we don't kill mid-transfer). The budget is a soft limit — it prevents runaway sync cycles but doesn't guarantee exact timing.

5. **Existing test impact**: The schema migration adds columns to existing tables. Tests that create `SqliteGameStateStore` will automatically get the new columns. Existing upsert tests should still pass (new columns have defaults). The `IntelStore` methods are tested separately in `test_sqlite_intel.py`.

6. **No new Python dependencies**: Everything uses stdlib (`csv`, `hashlib`, `subprocess`, `threading`, `tempfile`, `time`). The `sftp` binary is the only external requirement.

7. **Config backward compatibility**: If `intel_host` is not in the config, all intel features are disabled and invisible. Existing configs work unchanged. New config keys are only read when `intel_host` is present.

8. **HUD shutdown behavior change**: When intel IS configured, pressing `q` now shows a modal and does a final push before exiting. This adds ~1-5 seconds to shutdown. If the server is unreachable, the modal shows the failure for 1.5s then exits. Second ctrl+c always force-quits immediately. When intel is NOT configured, shutdown is instant (unchanged).
