# Feature Design: Shared Sector Intelligence

STATUS: ideation

## Use Cases (from user — do not modify)
1. I can push my discovered sector data (topology only — not my ship/cargo/turns) to a shared location so my corp mates can see what I've explored.
2. I can pull sector data that my corp mates have pushed, so I get their discoveries merged into my local DB.
3. When I pull data that conflicts with what I already have (e.g., port commodity levels), the freshest data wins based on UTC timestamp.
4. The system only exports sectors/ports/warps that I personally discovered — not data I imported from someone else (prevents re-sharing inflation).
5. I can configure the shared location in my profile config. All intel config fields work at both `[DEFAULT]` and `[profile:name]` levels with profile overriding default.
6. Push/pull are available as manual CLI commands (`tw intel push`, `tw intel pull`).
7. The HUD automatically syncs in the background on a configurable interval — pull on startup, push+pull during runtime, push on shutdown.
8. If the intel server config is not set on the profile, all sync functionality is disabled and invisible.
9. The HUD shutdown push shows a "Syncing Intel..." modal with a status line. First ctrl+c triggers graceful sync; second ctrl+c force-quits.
10. If a sync cycle fails, the HUD shows a blinking `! Intel E##` indicator in the header bar until the next successful sync.
11. The intel server is a Docker container (alpine + openssh, SFTP-only) that anyone can self-host. Operator adds player SSH public keys to grant access.
12. Docker container setup instructions go in the README.

## Problem
Players on the same corp explore different parts of the universe independently. Without sharing, each player only knows about sectors they've personally visited. Manual sharing (screenshots, verbal descriptions) is tedious and error-prone. Players need an automated way to pool their sector knowledge so the entire corp benefits from everyone's exploration — while keeping the system simple, self-hostable, and secure.

## Success Criteria
- [ ] `tw intel push` exports local discoveries as CSV and uploads via SFTP ← UC#1, UC#4, UC#6
- [ ] `tw intel pull` downloads other players' reports and merges into local DB ← UC#2, UC#6
- [ ] Port/commodity conflicts resolved by freshest `updated_at` timestamp (UTC epoch) ← UC#3
- [ ] Only records with `source IS NULL` are exported (local discoveries only) ← UC#4
- [ ] Intel config fields (`intel_host`, `intel_key`, `intel_port`, `intel_sync_interval`, `intel_sync_budget`, `intel_max_file_size`) work at `[DEFAULT]` and profile level ← UC#5
- [ ] HUD runs sync in a background worker — render loop never blocks on network I/O ← UC#7
- [ ] HUD syncs on startup (pull), on interval (push+pull), and on shutdown (push) ← UC#7
- [ ] Intel features completely disabled when `intel_host` not configured ← UC#8
- [ ] Shutdown shows sync modal; first ctrl+c syncs, second ctrl+c kills ← UC#9
- [ ] Failed sync shows blinking `! Intel E##` in header bar ← UC#10
- [ ] Docker container provides a ready-to-deploy SFTP-only intel server ← UC#11
- [ ] README documents how to run the Docker container and add player keys ← UC#12

## User-Facing Behavior

### Configuration

```ini
[DEFAULT]
intel_sync_interval = 300
intel_sync_budget = 30
intel_max_file_size = 10485760

[profile:saintcon]
db = ~/.local/share/tw-guidance-computer/saintcon.db
intel_host = intel.example.com
intel_key = ~/.ssh/tw_intel_ed25519
intel_port = 2222
```

- `intel_host`: SFTP server hostname. Master switch — if not set, intel is disabled entirely. Other intel fields ignored silently.
- `intel_key`: Path to SSH private key. Required if `intel_host` is set. Startup error if missing.
- `intel_port`: SSH port. Default 22.
- `intel_sync_interval`: Seconds between HUD sync cycles. Default 300.
- `intel_sync_budget`: Max seconds a single sync cycle can run. Must be less than `intel_sync_interval`. Default 30.
- `intel_max_file_size`: Max bytes per remote file to download. Default 10485760 (10MB).

### Startup Validation

- `intel_host` set but `intel_key` not set → error and exit: `"Error: intel_host is configured but intel_key is not set. Add intel_key to your profile."`
- `intel_key` path doesn't exist on disk → error and exit: `"Error: intel_key not found: ~/.ssh/tw_intel_ed25519"`
- `intel_sync_budget >= intel_sync_interval` → error and exit: `"Error: intel_sync_budget (45s) must be less than intel_sync_interval (30s). Sync cycles would overlap."`

### Player Identity

Identity is derived from the SHA-256 hash of the player's SSH public key (read from `intel_key` path + `.pub`). Full 64-character hex hash used as the identifier. No additional configuration needed.

This hash is used:
- As the directory/filename on the remote server (identifies your uploads)
- As the `source` tag on imported records in the local DB
- As the export filter (only export records where `source IS NULL`)

### CLI Commands

**`tw intel push`**
```
$ tw intel push
Exporting 142 sectors, 67 ports, 312 warps, 4 planets...
Uploading to intel.example.com:2222...
Done. Pushed 525 records.
```

**`tw intel pull`**
```
$ tw intel pull
Found 3 sources on remote.
Downloading a3f2b8c9d1e4f567... (45KB)
Downloading 7b1c9e2d4f6a8b03... (32KB)
Downloading e5d4c3b2a1f09876... (28KB)
Merging: +45 sectors, +23 ports, 12 ports updated (fresher), +89 warps
Done.
```

**Errors (CLI):**
```
$ tw intel push
Error [E24]: Connect failed: Connection timed out (intel.example.com:2222)
```

### HUD Behavior

**Normal operation (intel healthy):**
```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500
```

No indicator when sync is working. Silent success.

**Sync failure:**
```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500  │  ! Intel E24
```

`! Intel E##` displayed in red, bold, blinking (curses `A_BLINK`). Persists until next successful sync clears it.

**Shutdown modal (success):**
```
╔══════════ Syncing Intel ══════════╗
║                                   ║
║   Exporting warps...              ║
║                                   ║
╚═══════════════════════════════════╝
```

Status line updates: exporting sectors... exporting ports... transmitting... done.

**Shutdown modal (failure):**
```
╔══════════ Syncing Intel ══════════╗
║                                   ║
║   Push failed: server unreachable ║
║                                   ║
╚═══════════════════════════════════╝
```

Pauses briefly for user to read, then exits.

**Signal handling:**
- `q` key: Trigger graceful shutdown (show modal, push, exit)
- First ctrl+c (SIGINT): Same as `q` — trigger graceful shutdown with sync
- Second ctrl+c: Force quit immediately (standard Unix behavior)

### HUD Sync Algorithm

Sync runs in a background worker (thread or process), completely decoupled from the 250ms render loop.

**Pull with rotating offset:**
1. List all files on remote
2. Exclude own keyhash file
3. Compute start offset: `sync_counter % total_remote_files`
4. Starting from offset, process files sequentially until time budget expires
5. Increment sync_counter (in-memory, resets each session)

This guarantees all sources are eventually reached even if a single cycle can't process them all.

**Push:**
- Export all local records (`WHERE source IS NULL`) as CSV with trailing SHA-256 checksum line
- Upload via SFTP, overwriting previous file

**Each cycle:** push, then pull. Repeat on `intel_sync_interval`.

### File Integrity

Each uploaded CSV file ends with a checksum line:
```
#SHA256:a3f2b8c9d1e4f567890abcdef1234567890abcdef1234567890abcdef12345678
```

On pull, the receiver:
1. Reads the last line
2. If it starts with `#SHA256:` — validates hash against all preceding content
3. Match → file is valid, import it
4. Missing or mismatch → E52 (import data corrupt), skip this source

This detects partial uploads (connection died mid-transfer) without requiring atomic rename or multiple files on the server.

### Error Codes

| Code | Meaning |
|------|---------|
| E10 | Environment error (SFTP binary missing, no network stack) |
| E17 | Export failed (local DB read / CSV serialization error) |
| E24 | Connect failed (unreachable, timeout, DNS) |
| E31 | Auth failed (key rejected) |
| E38 | Write failed (SFTP upload error) |
| E45 | Read failed (SFTP download error, or file exceeds max size) |
| E52 | Import data corrupt (CSV parse failure, checksum mismatch) |
| E59 | Import failed (local DB write error on merge) |
| E66 | Key inaccessible (file gone mid-session) |

## Data Requirements

### Already Available
- All sector, port, warp, and planet data in SQLite
- Profile configuration infrastructure (Feature 002)
- `get_all_warps()`, `get_all_ports()`, sector/port/planet queries

### New Data Needed
- `source TEXT` column on sectors, ports, port_commodities, warps, planets (NULL = local, keyhash = imported)
- `updated_at REAL` column on same tables (UTC epoch, set by parser via `time.time()`)

### Storage
- No new tables. Columns added to existing tables.
- Server-side: filesystem directory with CSV files (one directory or file per player keyhash)

## Dependencies
- **Feature 002 (Profile-Based Configuration)**: Required for config infrastructure (`intel_*` keys in profile sections with `[DEFAULT]` cascade)
- **Docker**: For the intel server container (build/deploy artifact, not a Python dependency)
- **paramiko or subprocess**: For SFTP client operations (implementation detail — architect decides)

## Out of Scope
- Sharing player state (cargo, credits, turns, ship position)
- Real-time sync or push notifications
- Encryption of data at rest on the server (bucket ACL via SSH is the security boundary)
- Web UI or dashboard for viewing shared intel
- Automatic discovery of intel servers
- Per-user accounts on the server (single SFTP user, differentiated by key)
- Conflict resolution UI (freshest wins automatically, no user intervention)

## Open Questions
None — all resolved during discussion.

## TW Expert Notes
- TW2002 max universe size is 20,000 sectors (most servers run 1,000-5,000). A full export of a completely explored universe is well under 5MB.
- Port commodity quantities change as players trade. Sharing fresh commerce data is valuable for planning trade runs.
- Warp connections are static (don't change during gameplay). Sharing warps is purely additive.
- Sector regions are static. Planet presence is static.
- The competitive advantage of shared intel is significant — knowing the full warp graph lets you find optimal trade routes and safe paths that solo players can't.

## Docker Container (Intel Server)

**Image**: alpine + openssh-server, configured for SFTP-only with chroot.

**Operator workflow:**
1. `docker run -d -p 2222:22 -v ./authorized_keys:/etc/tw-intel/keys:ro -v ./data:/data tw-guidance-computer/intel-server`
2. Add a player: append their pubkey to `./authorized_keys`
3. Remove a player: remove their line from `./authorized_keys`

**Security configuration:**
- `ForceCommand internal-sftp` (no shell access)
- `ChrootDirectory /data` (jailed to data directory)
- Single shared SFTP user (all players authenticate as this user, differentiated by key)
- Revocation: remove key from authorized_keys, immediate effect

**Operator maintenance** (documented in README, no scripts needed):
- Data layout: one file per player keyhash in `/data/`. Plain CSV, human-inspectable.
- Remove a player's data: `rm /data/<keyhash>*`
- Full reset: `rm -rf /data/*`
- Inspect: `ls -la /data/`, `du -sh /data/*`, `cat /data/<keyhash>`
- Find corrupt files: `for f in /data/*; do expected=$(tail -1 "$f" | sed 's/#SHA256://'); actual=$(head -n -1 "$f" | sha256sum | cut -d' ' -f1); [ "$expected" != "$actual" ] && echo "CORRUPT: $f"; done`
- Find stale files (e.g., 30+ days): `find /data -type f -mtime +30 -ls`
- No custom scripts — standard filesystem commands cover all maintenance.

**README documents**: How to build/run the container, add/remove player keys, configure the client profile to connect, data layout explanation, and maintenance commands.

## Conflict Resolution

| Data | Strategy | Rationale |
|------|----------|-----------|
| Warps | Additive (INSERT OR IGNORE) | A warp exists or it doesn't. Static. |
| Planets | Additive (INSERT OR IGNORE) | Static presence. |
| Sectors | Take more complete (explored beats unexplored) | Region is static, explored status upgrades. |
| Ports/commodities | Freshest wins (compare `updated_at`) | Quantities change as players trade. |
