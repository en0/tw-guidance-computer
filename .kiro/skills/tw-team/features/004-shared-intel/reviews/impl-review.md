# Implementation Plan Review — Architect Adversary

## Verdict: PASS (with required notes)

The plan is architecturally sound. Dependency rules are respected, layer boundaries are clean, the threading model is safe, and the work unit decomposition is logical. No blocking issues found. The notes below are improvements the builder should incorporate during implementation, not reasons to reject the plan.

---

## Architecture Compliance

### Dependency Rule ✓
- Domain imports nothing from application or adapters.
- Application imports from domain and defines ports. Never from adapters.
- Adapters import from application and domain.
- No violations detected in any work unit.

### Domain Purity ✓
- `intel_csv.py` (Unit 4) is pure computation — uses `csv` and `hashlib` (stdlib, no I/O side effects from `hashlib`). Correct placement.
- `compute_identity` correctly moved to adapters (Unit 10) since it reads files. The plan's self-correction is noted and correct.
- Domain models remain unchanged — `updated_at`/`source` are adapter concerns. ✓

### Port Definitions ✓
- `IntelStore` and `IntelTransport` are Protocols speaking domain types. ✓
- Ports live in `application/ports/`. ✓
- Separation from `GameStateReader`/`GameStateWriter` is the right call — avoids bloating existing ports with unrelated bulk operations.

### Composition Root ✓
- All construction in `compose.py` (Unit 13). ✓
- Intel use cases passed directly to adapters rather than added to `UseCases` container — correct decision, avoids forcing all existing tests to change.

---

## Issues Found

### Issue 1: `IntelStore.get_local_ports()` return type mismatch with CSV serialization (MEDIUM)

The `IntelStore` port (Unit 2) defines:
```python
def get_local_ports(self) -> list[Port]: ...
```

But `serialize_intel()` (Unit 4) needs `updated_at` timestamps alongside each record to include in the CSV. The port returns bare `Port` objects — no timestamps attached.

The `ExportIntel` use case (Unit 7) calls `get_local_ports()` and passes results to `serialize_intel()`. But `serialize_intel(sectors, ports, warps, planets) -> str` — what are the types of those parameters? If they're bare domain objects, where do the `updated_at` values come from for the CSV?

**The fix**: The `get_local_*()` methods should return `list[tuple[DomainObject, float]]` (object + updated_at) — same shape as the `import_*()` methods accept. This makes the port symmetric and gives `serialize_intel()` the timestamps it needs.

Looking more carefully at Unit 2, `get_sector_updated_at()` and `get_port_updated_at()` exist as separate methods. But calling these per-record in a loop (N+1 query pattern) is inefficient for bulk export. The `get_local_*()` methods should return the timestamp alongside the domain object.

**Required change**: `get_local_sectors() -> list[tuple[Sector, float]]`, same for ports/warps/planets. Remove the separate `get_sector_updated_at()` and `get_port_updated_at()` methods — they're N+1 traps.

### Issue 2: `SyncIntelWorker` has mutable state and a `run()` loop — it's not a use case (LOW)

Unit 9 is placed in `application/` and described as "a use case that the HUD adapter runs in a thread." But it violates the Use Case Pattern codespec:

- Use cases have one public method: `execute()`. This has `run()`, `request_shutdown()`, `request_stop()`, `get_status()` — four public methods.
- Use cases are stateless orchestrators. This maintains `_sync_counter`, `_stop_requested`, `_shutdown_requested`, `_status` — it's a stateful service.
- Use cases don't contain `time.sleep()` loops.

This is a **worker/service**, not a use case. It orchestrates use cases (`PushIntel`, `PullIntel`) but is itself an application-layer service with lifecycle management.

**Acceptable as-is**: The plan places it in `application/` which is correct (it depends on ports and domain types, not on adapters). It's not a use case by the codespec definition, but it's correctly layered. The naming (`SyncIntelWorker`) already signals it's not a standard use case. No structural change needed — just don't mark it `@final` with `execute()` pretense. It's a `@final` service class.

### Issue 3: Thread safety of `SyncStatus` replacement is correct but under-specified (LOW)

The plan says: "Python's GIL makes single-reference assignment atomic."

This is correct for CPython but worth noting:
- The worker replaces `self._status = SyncStatus(...)` (atomic reference assignment under GIL).
- The render loop reads `self._status` (atomic reference read under GIL).
- No torn reads possible for reference assignment.

However, the plan should specify that `_status` is typed as `SyncStatus` (not `SyncStatus | None`) to avoid the render loop needing null checks after initial construction. Initialize with `SyncStatus()` (defaults: `last_error=None`, `shutdown_status=None`).

**No structural change needed** — just a note for the builder.

### Issue 4: `port_commodities` table doesn't exist — commodities are JSON in `ports` table (LOW)

The design review (Issue 1) mentions `port_commodities` as a table needing `source`/`updated_at` columns. The implementation plan's schema migration (Unit 5) lists:
```sql
ALTER TABLE ports ADD COLUMN source TEXT DEFAULT NULL;
ALTER TABLE ports ADD COLUMN updated_at REAL DEFAULT 0.0;
```

This is correct — commodities are stored as `commodities_json` within the `ports` table, not in a separate `port_commodities` table. The plan correctly migrates only the tables that actually exist (`sectors`, `ports`, `warps`, `planets`). No issue here — just confirming the plan correctly identified the actual schema.

### Issue 5: `serialize_intel` signature needs the `updated_at` values (MEDIUM)

Unit 4 defines:
```python
serialize_intel(sectors, ports, warps, planets) -> str
```

But the CSV format includes `updated_at` per record:
```
#TYPE:sectors
id,region,explored,updated_at
616,uncharted space,1,1716400000.0
```

The function needs to receive `list[tuple[Sector, float]]` (not bare `list[Sector]`). This is the same issue as Issue 1 — the types must flow consistently from store → use case → serializer.

**Required change**: `serialize_intel(sectors: list[tuple[Sector, float]], ports: list[tuple[Port, float]], warps: list[tuple[WarpConnection, float]], planets: list[tuple[Planet, float]]) -> str`

### Issue 6: `PullIntel` progress reporting for CLI (LOW)

The CLI (Unit 12) needs to print per-file download progress:
```
Downloading a3f2b8c9... (45KB)
```

But `PullIntel.execute()` (Unit 8) returns only the final `IntelMergeResult`. The CLI has no way to get per-file progress callbacks.

Options:
1. `PullIntel.execute()` accepts an optional callback `on_file: Callable[[str, int], None] | None`
2. The CLI calls `IntelTransport.list_files()` directly and loops itself (breaks use case encapsulation)
3. `PullIntel.execute()` returns a richer result including per-source details

**Recommendation**: Option 1 (callback) is cleanest. The use case remains the orchestrator; the callback is an optional progress hook. The HUD worker passes `None` (no progress needed). The CLI passes a print function.

This is a minor gap — the builder can resolve it. Not a structural flaw.

### Issue 7: Parallel group B has Unit 4 depending on Unit 1 domain types AND doing CSV serialization of `Port` — but `Port` has `commodities: list[PortCommodity]` (LOW)

The CSV format shows:
```
sector_id,name,port_class,port_type,commodities_json,updated_at
```

`Port.commodities` is a `list[PortCommodity]`. The serializer needs to flatten this to JSON for the CSV column. This is fine — `json.dumps()` of the commodity list is pure computation. Just noting that the serializer must handle the nested structure.

No change needed — the builder will handle this naturally.

### Issue 8: `SftpTransport.connect()` is called where? (LOW)

Unit 6 defines `connect()` and `disconnect()` on `IntelTransport`. But `disconnect()` is documented as "No-op (subprocess connections are stateless)." If connections are stateless (each operation is a separate subprocess), then `connect()` is just a connectivity check.

The use cases (`PushIntel`, `PullIntel`) don't show calling `connect()`/`disconnect()`. Who calls them?

Looking at the design: startup validation checks connectivity. The composition root or the CLI commands should call `connect()` as a pre-flight check. The background worker should call it at the start of each cycle.

**Recommendation**: Either:
- Remove `connect()`/`disconnect()` from the port (each method handles its own subprocess) and add a `verify_connectivity()` method for pre-flight checks.
- Or document that `PushIntel`/`PullIntel` call `connect()` at the start of `execute()`.

The current design leaves this ambiguous. Not blocking — the builder will figure it out — but the port contract should be explicit about lifecycle.

### Issue 9: `updated_at` on existing rows defaults to `0.0` — implications for first push after upgrade (INFORMATIONAL)

Risk Note 1 in the plan correctly identifies this:
> Existing rows get `source = NULL` and `updated_at = 0.0`. The `0.0` timestamp means existing data will be "older" than any freshly-pushed data from other players.

This means: after upgrading, Player A pushes their data (all with `updated_at = 0.0`). Player B pulls it. Player B already has the same sectors from their own exploration (also `updated_at = 0.0`). The "freshest wins" comparison for ports: `0.0 vs 0.0` — tie. What happens on a tie?

The plan doesn't specify tie-breaking behavior for `import_ports`. If `incoming_updated_at == existing_updated_at`, should the import skip (keep local) or overwrite?

**Recommendation**: On tie, keep local (`>` not `>=`). This prevents unnecessary churn and respects the principle that your own observations are preferred when freshness is equal.

---

## Design Review Issues Addressed

| Design Review Issue | Addressed? | How |
|---|---|---|
| #1: Missing `get_all_sectors()`/`get_all_planets()` | ✓ | New `IntelStore` port with `get_local_*()` methods |
| #2: `updated_at` parser modification | ✓ | Adapter sets `time.time()` on write — parser unchanged |
| #3: `source` column as adapter concern | ✓ | Adapter manages `source` — domain models unchanged |
| #4: Server-side write isolation trust model | ✓ | Architecture Decision #6 explicitly acknowledges trust assumption |
| #8: CSV format unspecified | ✓ | Architecture Decision #7 specifies sectioned format with type headers |
| #10: Schema migration | ✓ | Unit 5 specifies idempotent `ALTER TABLE ADD COLUMN` with try/except |

All medium/high design review issues are addressed. ✓

---

## Parallel Execution Conflicts

| Group | Units | Same File? | Conflict? |
|---|---|---|---|
| A | 1, 14 | No | None |
| B | 2, 3, 4, 10 | No (different dirs) | None |
| C | 5, 6 | No | None |
| G | 11, 12 | No (`tui.py` vs `cli_commands.py`) | None |

No parallel conflicts detected. ✓

---

## Threading Model Assessment

- **WAL mode**: Concurrent reads (render loop) and writes (sync worker) are safe. ✓
- **Atomic status**: `SyncStatus` frozen dataclass replaced by reference assignment. GIL-safe. ✓
- **No shared mutable state**: Worker owns its internal state. Render loop only reads the status reference. ✓
- **Daemon thread**: Worker thread is daemon — if main thread dies (second SIGINT), worker dies too. ✓

Threading model is sound. ✓

---

## CSV Placement Assessment

- **Serialization/deserialization** (`intel_csv.py`): Domain layer. Pure computation — takes domain objects + floats, returns string. No I/O. ✓
- **File writing** (temp file for upload): Happens in `PushIntel` use case... wait.

`PushIntel` (Unit 8) says: "Writes to a temp file. Calls `transport.upload(temp_file, ...)`."

Writing to a temp file IS I/O. This is happening in the application layer (`PushIntel` is in `application/`). This violates the "no I/O in application" rule.

**However**: Looking at the codespec more carefully — "I/O and external-system libraries stay in adapters. The domain and application layers never import `requests`, `boto3`, `pika`, `sqlalchemy`, or any library that performs I/O."

`tempfile` is stdlib and the write is a local implementation detail of passing data to the transport port. The alternative (passing the entire CSV string through the port's `upload()` method) would change the port signature to `upload(content: str, remote_name: str)` instead of `upload(local_path: Path, remote_name: str)`.

**Recommendation**: Change `IntelTransport.upload()` to accept `content: bytes | str` instead of `local_path: Path`. This eliminates the temp file from the use case entirely — the adapter handles writing to temp file internally if needed for subprocess stdin. This keeps the application layer I/O-free.

If the subprocess approach requires a file path (sftp `put` command needs a local file), then the temp file creation belongs in the adapter's `upload()` implementation, not in the use case.

**Required change**: `IntelTransport.upload(content: str, remote_name: str) -> None` — adapter handles temp file internally.

---

## Summary of Required Changes

1. **`get_local_*()` return types**: Must return `list[tuple[DomainObject, float]]` to include `updated_at`. Remove separate `get_*_updated_at()` methods.
2. **`serialize_intel()` signature**: Must accept `list[tuple[T, float]]` parameters, not bare domain object lists.
3. **`IntelTransport.upload()` signature**: Accept `content: str` not `local_path: Path`. Adapter handles temp file internally. Keeps application layer I/O-free.
4. **Tie-breaking on `import_ports`**: Specify `>` (strict greater-than) for freshness comparison. On tie, keep local.

## Notes for Builder (non-blocking)

- `SyncIntelWorker` is a service, not a use case. Don't force `execute()` pattern on it.
- Initialize `_status = SyncStatus()` in constructor — never `None`.
- `connect()`/`disconnect()` lifecycle on `IntelTransport` needs clarification — consider making each operation self-contained (subprocess is stateless anyway) and adding a separate `verify_connectivity()` for pre-flight.
- `PullIntel` may need a progress callback for CLI output. Builder can add `on_progress: Callable | None = None` parameter.
- Port commodity serialization: flatten `list[PortCommodity]` to JSON string in the CSV column. Standard `json.dumps()`.
