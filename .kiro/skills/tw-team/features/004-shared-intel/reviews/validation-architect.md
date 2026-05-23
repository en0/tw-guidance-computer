# Architect Validation — Feature 004: Shared Sector Intelligence

## Verdict: PASS (with notes)

All 4 required changes from the adversarial review are incorporated. Dependency rules are clean. Codespec compliance is strong. One minor dead-field issue noted below — not blocking.

---

## Required Changes Verification

### 1. `get_local_*()` return `list[tuple[DomainObject, float]]` ✓

**Port** (`application/ports/intel_store.py`):
```python
def get_local_sectors(self) -> list[tuple[Sector, float]]: ...
def get_local_ports(self) -> list[tuple[Port, float]]: ...
def get_local_warps(self) -> list[tuple[WarpConnection, float]]: ...
def get_local_planets(self) -> list[tuple[Planet, float]]: ...
```

**Implementation** (`adapters/outbound/sqlite_store.py`): All four methods SELECT `updated_at` alongside domain fields and return `(DomainObject, float)` tuples. No separate `get_sector_updated_at()` / `get_port_updated_at()` methods exist — they were removed as required.

### 2. `serialize_intel()` accepts `list[tuple[T, float]]` parameters ✓

**Signature** (`domain/intel_csv.py`):
```python
def serialize_intel(
    sectors: list[tuple[Sector, float]],
    ports: list[tuple[Port, float]],
    warps: list[tuple[WarpConnection, float]],
    planets: list[tuple[Planet, float]],
) -> str:
```

Types flow consistently: store → use case → serializer. No N+1 queries.

### 3. `IntelTransport.upload()` accepts `content: str` ✓

**Port** (`application/ports/intel_transport.py`):
```python
def upload(self, content: str, remote_name: str) -> None:
```

**Adapter** (`adapters/outbound/sftp_transport.py`): Creates temp file internally in `upload()`, writes content, runs sftp `put`, cleans up in `finally` block. Application layer is I/O-free.

**Use case** (`application/push_intel.py`):
```python
content = self._export.execute()
self._transport.upload(content, self._identity)
```

No temp file, no Path import, no I/O in the application layer.

### 4. Tie-breaking on `import_ports` uses strict `>` ✓

**Implementation** (`adapters/outbound/sqlite_store.py`, line ~432):
```python
elif updated_at > row[0]:
```

Strict greater-than. On tie (equal timestamps), the `elif` is not entered, count is not incremented, local record is preserved.

**Tests confirm**: `test_tie_keeps_local_port` inserts local with `updated_at=1000.0`, imports with same timestamp, asserts `count == 0` and local name preserved.

---

## Dependency Rule Compliance ✓

| Layer | Imports From | Violations |
|-------|-------------|-----------|
| `domain/models/intel.py` | `domain/exceptions` only | None |
| `domain/intel_csv.py` | `domain/exceptions`, `domain/models` | None |
| `application/ports/intel_store.py` | `domain/models` | None |
| `application/ports/intel_transport.py` | `domain/models` | None |
| `application/export_intel.py` | `application/ports`, `domain/intel_csv` | None |
| `application/import_intel.py` | `application/ports`, `domain/intel_csv`, `domain/models` | None |
| `application/push_intel.py` | `application/export_intel`, `application/ports` | None |
| `application/pull_intel.py` | `application/import_intel`, `application/ports`, `domain/exceptions`, `domain/models` | None |
| `application/sync_intel_worker.py` | `application/push_intel`, `application/pull_intel`, `domain/exceptions`, `domain/models` | None |
| `adapters/outbound/sftp_transport.py` | `application/ports`, `domain/exceptions`, `domain/models` | None |
| `adapters/outbound/intel_identity.py` | `domain/exceptions`, `domain/models` | None |
| `adapters/inbound/sync_modal.py` | Nothing (pure function) | None |
| `adapters/inbound/tui.py` | `application/sync_intel_worker` (TYPE_CHECKING only) | None |
| `adapters/inbound/cli_commands.py` | `application/ports`, `application/push_intel`, `application/pull_intel`, `domain/exceptions`, `domain/models` | None |
| `compose.py` | All layers (correct — it's the composition root) | None |

Strict one-way dependency: adapters → application → domain. No violations.

---

## Codespec Compliance

### Frozen Dataclasses ✓
- `IntelConfig`: `@dataclass(frozen=True)`, validates in `__post_init__`, raises `ValidationError`
- `RemoteFile`: `@dataclass(frozen=True)`, validates in `__post_init__`, raises `ValidationError`
- `IntelMergeResult`: `@dataclass(frozen=True)`, validates non-negative, derived `total` property
- `SyncStatus`: `@dataclass(frozen=True)`, validates `last_error` not empty-string

### @final ✓
- All use cases: `ExportIntel`, `ImportIntel`, `PushIntel`, `PullIntel`, `SyncIntelWorker`
- Adapter: `SftpTransport`
- Composition root: `AppContext`

### @override ✓
- `SftpTransport`: 3 methods (`upload`, `download`, `list_files`)
- `SqliteGameStateStore`: 8 methods (`get_local_*` × 4, `import_*` × 4)

### Exception Hierarchy ✓
- Flat: `IntelError(GuidanceError)` base, 4 leaf exceptions one level deep
- All in `domain/exceptions.py`
- Adapter translates subprocess errors → domain exceptions with `from e`

### Port Definitions ✓
- `IntelStore`: Protocol, speaks domain types, documents exception contract
- `IntelTransport`: Protocol, speaks domain types (`str`, `RemoteFile`), stateless
- Adapter explicitly inherits: `SftpTransport(IntelTransport)`, `SqliteGameStateStore(..., IntelStore)`

### Composition Root ✓
- All construction in `compose.py`
- Intel components constructed conditionally (when `intel_host` configured)
- Entry points (`hud.py`, `cli.py`) don't construct intel components directly
- `UseCases` container NOT modified — intel use cases passed separately

### Use Case Pattern ✓
- One class per file, one `execute()` method each
- Dependencies injected via constructor
- `SyncIntelWorker` correctly treated as a service (has `run()`, `request_shutdown()`, `get_status()`) — not forced into `execute()` pattern

### Testing Strategy ✓
- 11 test files mirror source structure
- Tests exist for domain, application, adapters, and integration layers

---

## Notes (Non-Blocking)

### `IntelMergeResult.ports_updated` is a dead field

The `IntelMergeResult` dataclass has a `ports_updated` field, but `ImportIntel.execute()` never populates it:
```python
ports_added = self._store.import_ports(ports, source)
return IntelMergeResult(sectors_added=..., ports_added=ports_added, ...)
# ports_updated defaults to 0
```

The `IntelStore.import_ports()` port returns a single `int` (combined inserts + updates). The CLI prints `"{result.ports_updated} ports updated (fresher)"` which will always show 0.

**Impact**: Cosmetic — the CLI output is slightly misleading. The total count in `ports_added` includes both new inserts and freshness-based updates.

**Fix (future)**: Either change `import_ports` to return `tuple[int, int]` (added, updated), or remove `ports_updated` from `IntelMergeResult` and rename `ports_added` to `ports_changed`.

Not blocking because the merge logic itself is correct — the display is just imprecise.

### `connect()`/`disconnect()` lifecycle correctly removed

The review recommended clarifying or removing the lifecycle methods. The builder chose to remove them entirely — the port is now stateless with 3 methods (`upload`, `download`, `list_files`). Each operation is self-contained via subprocess. This is the cleaner design.

### Docker container is minimal and correct

Alpine + openssh-server, `ForceCommand internal-sftp`, `ChrootDirectory /data`, no password auth, no root login. Trust model documented.

---

## Summary

The implementation faithfully follows the plan and incorporates all 4 required changes from the adversarial review. Architecture is clean, codespecs are respected, and the one noted issue (dead `ports_updated` field) is cosmetic. The feature is ready for PM validation.
