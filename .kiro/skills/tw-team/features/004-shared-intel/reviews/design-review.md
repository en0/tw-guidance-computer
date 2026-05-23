# Design Review — PM Adversary

## Verdict: PASS (with notes)

## Use Case Fidelity

All 12 user use cases are present verbatim in the "Use Cases" section. None dropped, merged, or reinterpreted. ✓

## Use Case Coverage

| UC | Requirement | Design Coverage | Status |
|----|-------------|----------------|--------|
| 1 | Push discovered sector data (topology only — not ship/cargo/turns) to shared location for corp mates | `tw intel push` exports sectors/ports/warps/planets as CSV, uploads via SFTP. Out of Scope explicitly excludes player state. | ✓ |
| 2 | Pull sector data that corp mates pushed, merged into local DB | `tw intel pull` downloads other players' files, merges with conflict resolution. | ✓ |
| 3 | Conflicts resolved by freshest UTC timestamp | Conflict Resolution table: ports/commodities use "freshest wins (compare `updated_at`)". `updated_at REAL` column (UTC epoch) added to tables. | ✓ |
| 4 | Only exports personally discovered data — not re-shared imports | `source TEXT` column: NULL = local, keyhash = imported. Export filter: `WHERE source IS NULL`. | ✓ |
| 5 | Shared location configurable in profile config, works at `[DEFAULT]` and `[profile:name]` levels | Config section shows `intel_host`, `intel_key`, `intel_port` in profile section. Success criterion explicitly states both levels. | ✓ |
| 6 | Push/pull available as manual CLI commands | `tw intel push` and `tw intel pull` documented with example output. | ✓ |
| 7 | HUD auto-syncs in background on configurable interval — pull on startup, push+pull during runtime, push on shutdown | HUD Sync Algorithm section: background worker, `intel_sync_interval` config, startup pull, interval push+pull, shutdown push. | ✓ |
| 8 | If intel server config not set, all sync disabled and invisible | `intel_host` documented as "Master switch — if not set, intel is disabled entirely." Success criterion: "Intel features completely disabled when `intel_host` not configured." | ✓ |
| 9 | Shutdown push shows "Syncing Intel..." modal with status line. First ctrl+c syncs, second force-quits. | Shutdown modal mockups shown (success + failure). Signal handling section: first ctrl+c = graceful sync, second = force quit. | ✓ |
| 10 | Failed sync shows blinking `! Intel E##` in header bar until next successful sync | HUD Behavior section: red bold blinking indicator, persists until next success clears it. Error code table provided. | ✓ |
| 11 | Intel server is a Docker container (alpine + openssh, SFTP-only), self-hostable, operator adds SSH pubkeys | Docker Container section: alpine + openssh-server, ForceCommand internal-sftp, ChrootDirectory, operator adds keys to authorized_keys. | ✓ |
| 12 | Docker container setup instructions go in README | README documents section lists: build/run, add/remove keys, configure client, data layout, maintenance. | ✓ |

## Issues Found

### Issue 1: No existing bulk export methods for sectors or planets — port extensions needed but not acknowledged (MEDIUM)

The design says under "Already Available":
> All sector, port, warp, and planet data in SQLite
> `get_all_warps()`, `get_all_ports()`, sector/port/planet queries

This is misleading. The `GameStateReader` Protocol has `get_all_warps()` and `get_all_ports()`, but there is NO `get_all_sectors()` and NO `get_all_planets()`. The only sector query is `get_sector(sector_id: int) -> Sector | None` (requires knowing the ID). The only planet query is `has_planet(sector_id: int) -> bool` (returns boolean, not planet data).

To export sectors and planets for push, the implementation will need:
1. `get_all_sectors() -> list[Sector]` — new port method
2. `get_all_planets() -> list[Planet]` — new port method (or at minimum a bulk query)

Additionally, the export filter (`WHERE source IS NULL`) requires the `source` column to exist, which means ALL existing query methods need to be aware of this new column. The `upsert_sector`, `upsert_port`, `upsert_warp`, `upsert_planet` methods will need to accept or set `source` and `updated_at` values.

The design correctly identifies the new columns in "New Data Needed" but categorizes the query infrastructure as "Already Available" when it isn't.

**Impact**: Medium. The architect will figure this out, but the design underestimates the scope of port/adapter changes needed. This isn't just "add columns" — it's new port methods AND modifications to existing port method signatures (or new overloaded methods for import vs. local write).

### Issue 2: `updated_at` column requires parser modification — not mentioned in Dependencies (MEDIUM)

The design says:
> `updated_at REAL` column on same tables (UTC epoch, set by parser via `time.time()`)

This means the parser (`ParseLogChunk`) must be modified to set `updated_at` on every record it writes. Currently, `upsert_sector(sector)`, `upsert_port(port)`, `upsert_warp(warp)`, and `upsert_planet(planet)` take domain objects that have NO `updated_at` field. The domain models (`Sector`, `Port`, `WarpConnection`, `Planet`) are frozen dataclasses without timestamps.

Options for the architect:
1. Add `updated_at` to domain models (changes the domain contract)
2. Have the adapter set `updated_at = time.time()` on every write (adapter-level concern)
3. Add new port methods for import that accept timestamps

Option 2 is cleanest (adapter sets timestamp on write, import methods accept explicit timestamps). But the design doesn't acknowledge this as a design decision or dependency. It just says "set by parser via `time.time()`" which implies option 1 (parser sets it), but the parser calls domain-typed port methods.

**Impact**: Medium. This is an architectural decision that affects the domain/adapter boundary. The design should at least acknowledge the tension rather than hand-waving "set by parser."

### Issue 3: Conflict resolution for sectors says "explored beats unexplored" but `updated_at` is the stated mechanism (LOW)

UC#3 says: "the freshest data wins based on UTC timestamp." The Conflict Resolution table says:
- Sectors: "Take more complete (explored beats unexplored)"
- Ports/commodities: "Freshest wins (compare `updated_at`)"

For sectors, the strategy is NOT timestamp-based — it's "explored beats unexplored." This is a different strategy than what UC#3 describes. UC#3 says "freshest data wins" but the design applies that only to ports/commodities, not sectors.

Is this a violation? UC#3 says "When I pull data that conflicts with what I already have (e.g., port commodity levels), the freshest data wins." The parenthetical "(e.g., port commodity levels)" suggests the user was thinking primarily about ports. The sector strategy (explored > unexplored) is arguably more correct for static data — a sector's region doesn't change, so "freshest" is meaningless; "most complete" is the right merge strategy.

**Impact**: Low. The design makes a reasonable interpretation. The user's example was ports, and ports DO use freshest-wins. Sectors use a more appropriate strategy for static data. Not a UC violation — it's a refinement.

### Issue 4: Player identity requires `.pub` file to exist — not validated at startup (LOW)

The design says identity is derived from "the player's SSH public key (read from `intel_key` path + `.pub`)." Startup validation checks:
- `intel_key` not set → error
- `intel_key` path doesn't exist → error

But it does NOT check that `intel_key + ".pub"` exists. If the user has `~/.ssh/tw_intel_ed25519` (private key) but no `~/.ssh/tw_intel_ed25519.pub` (public key), the identity derivation will fail at runtime (during first push/pull) rather than at startup.

**Impact**: Low. Easy to add to startup validation. The architect will likely catch this. But the design's startup validation section is incomplete.

### Issue 5: UC#1 says "topology only" but design exports port commodity quantities (INFORMATIONAL)

UC#1 says: "I can push my discovered sector data (topology only — not my ship/cargo/turns)."

The parenthetical clarifies what "topology only" excludes: ship state, cargo, turns. The design exports sectors, ports (including commodity quantities), warps, and planets. Port commodity quantities (how much fuel ore a port has) are arguably NOT topology — they're dynamic commerce data.

However, UC#3 explicitly mentions "port commodity levels" as data that gets shared and conflict-resolved. So the user clearly intends to share port data including quantities. The "topology only" in UC#1 is clarifying that PLAYER state isn't shared, not that port commerce data is excluded.

**Impact**: Informational. No contradiction — UC#1's "topology only" is about excluding player state, and UC#3 confirms port data is shared. The design is consistent with the full set of use cases.

### Issue 6: HUD sync algorithm says "push, then pull" but UC#7 says "pull on startup" (LOW)

UC#7: "pull on startup, push+pull during runtime, push on shutdown."

The design's HUD Sync Algorithm section says: "Each cycle: push, then pull." This is the runtime behavior. But the startup behavior is specified separately: "pull on startup." And shutdown: "push on shutdown."

The design correctly handles all three phases:
- Startup: pull only ✓
- Runtime: push then pull ✓
- Shutdown: push only ✓

But the "Each cycle: push, then pull" statement could be misread as applying to ALL cycles including startup. The design should be clearer that the startup cycle is pull-only.

Looking more carefully at the success criterion: "HUD syncs on startup (pull), on interval (push+pull), and on shutdown (push)" — this is unambiguous. The algorithm section is slightly ambiguous but the success criterion is clear.

**Impact**: Low. Success criterion is precise. Builder will follow the criterion.

### Issue 7: `intel_sync_budget` enforcement mechanism unspecified (LOW)

The design says `intel_sync_budget` is "Max seconds a single sync cycle can run" and validates that it's less than `intel_sync_interval`. But it doesn't specify HOW the budget is enforced during a sync cycle.

Options:
- Kill the SFTP connection after N seconds (abrupt, may corrupt upload)
- Check elapsed time between file downloads and stop pulling new files (graceful)
- Use a thread timeout (platform-dependent behavior)

The pull algorithm says "process files sequentially until time budget expires" — this implies option 2 (check between files). But what about push? If the upload itself takes longer than the budget (large file, slow connection), does it get killed mid-upload?

**Impact**: Low. The architect will specify this. The design's intent is clear (don't let sync run forever), but the enforcement granularity is unspecified.

### Issue 8: No specification of CSV format (LOW)

The design says data is exported as CSV but doesn't specify:
- Column order
- Header row presence
- Quoting rules (port names can contain commas: "Trader Vic's, Class 6")
- How multiple record types (sectors, ports, warps, planets) are represented in a single file
- Delimiter choice

Is it one CSV file with mixed record types? Four separate sections? Four separate files per player?

The design says "one file per player keyhash" on the server, which implies a single file containing all record types. But the format of that file is unspecified.

**Impact**: Low. Implementation detail for the architect. But the design should at least state whether it's one file or multiple, and whether record types are mixed or sectioned.

### Issue 9: Docker container security — single shared SFTP user means any player can overwrite another's file (MEDIUM)

The design says:
- "Single shared SFTP user (all players authenticate as this user, differentiated by key)"
- Data layout: "one file per player keyhash in `/data/`"

If all players authenticate as the same SFTP user and are chrooted to `/data/`, then any player can:
1. Read any other player's file (intended — that's how pull works)
2. **Overwrite or delete** any other player's file (unintended?)

The design doesn't address write isolation. A malicious player (or a bug in the client) could overwrite another player's data file. The client is supposed to only write to its own keyhash file, but the server doesn't enforce this.

**Mitigations the design could specify:**
- Server-side: per-key `ChrootDirectory` or `ForceCommand` with path restrictions (complex with single user)
- Client-side: trust the client to only write its own file (current implicit assumption)
- Accept the risk: corp mates are trusted (reasonable for a game tool)

The design's Out of Scope says "Per-user accounts on the server (single SFTP user, differentiated by key)" — so multi-user isolation is explicitly deferred. But the RISK of one player corrupting another's data isn't acknowledged.

**Impact**: Medium. For a corp tool among trusted players, this is acceptable. But the design should acknowledge the trust assumption explicitly rather than leaving it as an unaddressed security gap. A single `rm /data/*` from any authenticated player wipes everyone's intel.

### Issue 10: `source` column on existing tables is a schema migration — not addressed (LOW)

Adding `source TEXT` and `updated_at REAL` columns to 5 existing tables requires a schema migration for existing databases. The design says "Columns added to existing tables" but doesn't address:
- How existing rows get default values (presumably `source = NULL`, `updated_at = 0.0` or current time)
- Whether this requires a migration script or just `ALTER TABLE ADD COLUMN`
- Whether the migration is backward-compatible (old code reading new schema, new code reading old schema)

SQLite's `ALTER TABLE ADD COLUMN` with defaults handles this gracefully, but the design should acknowledge it as a migration concern.

**Impact**: Low. SQLite makes this easy. But it's a deployment concern for existing users upgrading.

## Success Criteria Testability

| Criterion | Testable? | How |
|-----------|-----------|-----|
| `tw intel push` exports and uploads | ✓ | Mock SFTP server, verify CSV content and upload |
| `tw intel pull` downloads and merges | ✓ | Seed remote with test files, verify local DB after pull |
| Freshest `updated_at` wins for ports | ✓ | Import older and newer records, verify newer wins |
| Only `source IS NULL` exported | ✓ | Import records, push, verify imported records absent from export |
| Config fields at both levels | ✓ | Set in `[DEFAULT]`, override in profile, verify resolution |
| Background worker doesn't block render | ✓ | Simulate slow network, verify HUD refresh continues at 250ms |
| Startup pull, interval push+pull, shutdown push | ✓ | Mock SFTP, verify call sequence |
| Disabled when `intel_host` not set | ✓ | Omit config, verify no sync attempts |
| Shutdown modal + signal handling | ✓ | Send SIGINT, verify modal appears then exits |
| Blinking error indicator | ✓ | Fail a sync, verify indicator appears; succeed, verify cleared |
| Docker container SFTP-only | ✓ | Build container, attempt shell (rejected), attempt SFTP (works) |
| README documentation | ✓ | File exists with required sections |

All criteria are measurable and testable. ✓

## Data Availability

| Data | Available? | Source |
|------|-----------|--------|
| Sectors (bulk export) | ⚠️ | Data in SQLite but no `get_all_sectors()` method exists (see Issue 1) |
| Ports (bulk export) | ✓ | `get_all_ports()` exists |
| Warps (bulk export) | ✓ | `get_all_warps()` exists |
| Planets (bulk export) | ⚠️ | Data in SQLite but no `get_all_planets()` method exists (see Issue 1) |
| Port commodities | ✓ | Embedded in `Port.commodities` (JSON in SQLite) |
| Source tracking | ❌ | New column needed on 5 tables |
| Updated timestamps | ❌ | New column needed on 5 tables |
| Config infrastructure | ✓ | `get_config_value()` exists on `IniProfileStore` (Feature 003 added it) |
| Profile-level config | ✓ | `configparser` `[DEFAULT]` cascade works (Feature 002) |

## Scope Check

No scope creep detected. The design explicitly defers:
- Sharing player state
- Real-time sync / push notifications
- Encryption at rest
- Web UI / dashboard
- Auto-discovery of servers
- Per-user server accounts
- Conflict resolution UI

The Docker container specification is within scope (UC#11 explicitly requests it). The error code system is a reasonable design detail for UC#10 (the user asked for `E##` format). The file integrity checksum is a reasonable robustness measure for a network-based feature — not scope creep.

The rotating offset pull algorithm is an implementation detail that could be considered over-specification for a design doc, but it's solving a real problem (time-budgeted partial sync) that the architect would need to solve anyway. Acceptable.

## Dependency Risk

- **Feature 002 (Profile-Based Configuration)**: Complete. Config infrastructure available. ✓
- **Feature 003 (Safe Harbor)**: Added `get_config_value()` to `IniProfileStore`. Available. ✓
- **Docker**: External build artifact. No Python dependency. Low risk.
- **SFTP client library**: `paramiko` or subprocess — architect decides. Both are well-established. Low risk.

## Summary

The design is faithful to all 12 use cases, well-scoped, and the conflict resolution strategy is sound. The main gaps are:

1. **Missing bulk query methods** (Issue 1): `get_all_sectors()` and `get_all_planets()` don't exist on the port. The design claims this data is "Already Available" when the query path isn't.
2. **`updated_at` parser integration** (Issue 2): Adding timestamps to writes requires either domain model changes or adapter-level timestamp injection — an architectural decision the design hand-waves.
3. **Server-side write isolation** (Issue 9): Any authenticated player can overwrite any file. Acceptable for trusted corp mates but the trust assumption should be explicit.

None of these are design FAILURES — they're implementation gaps the architect will resolve. The use cases are all satisfied, success criteria are testable and traceable, and scope is well-controlled. The feature is ready for planning.
