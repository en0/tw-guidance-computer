# UI Spec: Shared Sector Intelligence

## Interface
Both (HUD + CLI)

## Information Priority
1. Error indicator — must be noticed when sync is broken (HUD header bar)
2. Shutdown progress — player needs confidence data was saved before exit (HUD modal)
3. CLI push/pull progress — feedback during potentially slow network operations (CLI)

## HUD: Error Indicator

### Layout

Appended to the existing status bar (row 1), right-aligned after Credits:

Wide terminal (≥90 columns):
```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500  │  ! Intel E24
```

Narrow terminal (<90 columns):
```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500  │  ! E24
```

### Placement

- Row 1, appended after the Credits field
- Separator: `  │  ` (same style as existing separators)
- Wide form (≥90 cols): `! Intel E##` (13 chars with separator) — full context
- Narrow form (<90 cols): `! E##` (9 chars with separator) — compact, still identifiable
- Threshold check: `max_x >= 90` determines which form to render
- If terminal is too narrow for even the compact form (existing header + 9 chars > max_x), the indicator is suppressed entirely — player uses CLI `tw intel status` to check

### Color Scheme
- `! Intel E##` / `! E##`: red bold + `A_REVERSE` (curses color pair 4 with `A_BOLD | A_REVERSE`) — red background, guaranteed visible on all terminals
- `A_BLINK` added as a bonus attribute (`A_BOLD | A_REVERSE | A_BLINK`) — enhances attention on terminals that support it, but `A_REVERSE` alone is sufficient for visibility
- Separator `│`: yellow (curses color pair 3) — matches existing separators

### Update Triggers
- Appears: when a background sync cycle fails (any error code E10–E66)
- Disappears: when the next sync cycle succeeds
- Refresh: standard 250ms HUD tick (indicator state read from sync worker status)

### States
- **Normal (sync healthy or intel disabled)**: indicator not rendered, row 1 looks exactly as it does today
- **Error**: `  │  ! Intel E##` or `  │  ! E##` appended after Credits (width-dependent)
- **Intel not configured**: no indicator, no change to header — completely invisible

## HUD: Shutdown Modal

### Layout

Centered overlay using the same `╔═╗║╚═╝` box-drawing pattern as the RED ALERT overlay from Feature 003:

```
╔═══════════ Syncing Intel ═══════════╗
║                                     ║
║   Exporting sectors...              ║
║                                     ║
╚═════════════════════════════════════╝
```

Dimensions: dynamic width × 5 rows (height fixed). Width = `max(len(title_padded), len(longest_status_msg)) + 6` (2 border + 4 padding). Minimum width: 39 characters (accommodates `Push failed: server unreachable` = 31 chars + 4 padding + 2 border + 2 inner padding = 39).

### Content States

The status line (row 3 inside the box) updates as the sync progresses:

```
Exporting sectors...
Exporting ports...
Exporting warps...
Transmitting...
Done.
```

On failure:
```
Push failed: <reason>
```

Where `<reason>` is a short human-readable string derived from the error code (e.g., "server unreachable", "auth failed", "write error"). Failure reasons are truncated to 25 characters if longer, ensuring the full status line never exceeds 33 characters (`Push failed: ` = 13 + 25 max reason = 38 content, fits within 39-char box).

### Color Scheme
- Box border (`╔═╗║╚═╝`): cyan bold (curses color pair 2) — informational, not alarming
- Title text `Syncing Intel`: cyan bold (curses color pair 2) — matches border
- Status line (progress): green (curses color pair 1) — positive action in progress
- Status line (failure): red bold (curses color pair 4) — error state
- Status line ("Done."): green (curses color pair 1) — success

### Rendering

- Follows the same centered-box pattern as `_render_alert_overlay`:
  - `start_y = (max_y - box_height) // 2`
  - `start_x = (max_x - box_width) // 2`
- Rendered on top of all other content (drawn last in the render loop)
- Box height: 5 rows (border + padding + status + padding + border)

### Z-Order: RED ALERT vs. Shutdown Modal

If the player is in RED ALERT state (turns < 50) when `q` is pressed:
- The shutdown modal **replaces** the RED ALERT overlay — only one overlay renders at a time
- Rationale: shutdown is the active operation requiring feedback; the alert is informational and no longer actionable once the player has decided to quit
- Implementation: the render loop checks `if shutting_down: render_shutdown_modal() elif alert_active: render_alert_overlay()`

### Update Triggers
- Appears: when `q` is pressed or first SIGINT received
- Status line updates: as each export/upload phase completes (render loop continues at 250ms)
- Disappears: after "Done." displays for 500ms, then HUD exits
- On failure: displays failure message for 1500ms, then HUD exits

### Interaction

- While modal is visible, all other keybindings are disabled
- Second ctrl+c (SIGINT): force-quit immediately, modal disappears, process exits
- No dismiss key — modal auto-clears on completion or failure

## CLI: `tw intel push`

### Syntax
```
tw intel push [--profile NAME]
```

### Output Format

Success:
```
Exporting 142 sectors, 67 ports, 312 warps, 4 planets...
Uploading to intel.example.com:2222...
Done. Pushed 525 records.
```

Failure:
```
Error [E24]: Connect failed: Connection timed out (intel.example.com:2222)
```

### Output Details
- Line 1: summary of what's being exported (counts from local DB where `source IS NULL`)
- Line 2: destination confirmation (host:port from config)
- Line 3: completion with total record count
- All output to stdout; errors to stderr with exit code 1
- If nothing to export: `Nothing to push. No local discoveries found.`

## CLI: `tw intel pull`

### Syntax
```
tw intel pull [--profile NAME]
```

### Output Format

Success:
```
Found 3 sources on remote.
Downloading a3f2b8c9... (45KB)
Downloading 7b1c9e2d... (32KB)
Downloading e5d4c3b2... (28KB)
Merging: +45 sectors, +23 ports, 12 ports updated (fresher), +89 warps
Done.
```

Failure (connect):
```
Error [E24]: Connect failed: Connection timed out (intel.example.com:2222)
```

Failure (corrupt file):
```
Downloading a3f2b8c9... (45KB)
Warning [E52]: Skipping a3f2b8c9 — checksum mismatch
Downloading 7b1c9e2d... (32KB)
Merging: +12 sectors, +8 ports, 3 ports updated (fresher), +22 warps
Done.
```

### Output Details
- Keyhash truncated to first 8 chars for readability (UI decision — design doc shows full hash, but 8 chars is sufficient for visual identification and keeps output scannable)
- File size shown in human-readable format (KB/MB)
- Per-file corruption is a warning (continues with remaining sources), not a fatal error
- Merge summary shows: new sectors added, new ports added, ports updated by freshness, new warps added
- If no remote sources found: `No intel sources found on remote.`
- If own file is the only one: `No other players' intel found on remote.`

## CLI: Configuration Errors

These fire before any network operation:

```
Error: intel_host is configured but intel_key is not set. Add intel_key to your profile.
```

```
Error: intel_key not found: ~/.ssh/tw_intel_ed25519
```

Output to stderr, exit code 1.

## Data Requirements

### HUD Error Indicator
- Sync worker exposes a status field: `last_error: str | None` (e.g., `"E24"` or `None`)
- Render loop reads this field each tick (thread-safe read of a simple value)
- No new store queries needed

### HUD Shutdown Modal
- Sync worker exposes a progress field: `shutdown_status: str | None` (e.g., `"Exporting ports..."`)
- Render loop reads this field each tick while in shutdown state
- No new store queries needed (export logic is in the sync worker)

### CLI Commands
- Export query: `SELECT ... FROM sectors/ports/warps/planets WHERE source IS NULL` (count + data)
- Import merge: existing upsert patterns with `updated_at` comparison
- SFTP connection details from profile config

## Interaction Notes

### HUD
- No new keybindings added (existing `q` triggers shutdown which now includes sync modal)
- Error indicator is passive — no way to dismiss it manually (clears on next successful sync)
- Shutdown modal blocks all input except second ctrl+c
- If intel is not configured (`intel_host` absent), the HUD behaves identically to today — no modal on quit, no indicator, no background worker started

### CLI
- Commands are blocking (wait for network operations to complete)
- Progress lines print as each phase completes (not buffered)
- Ctrl+c during CLI push/pull: standard SIGINT behavior (abort, partial upload may exist on server — next push overwrites cleanly)

### Signal Handling (HUD)
| Signal | State | Behavior |
|--------|-------|----------|
| `q` key | Normal | Show sync modal → push → exit |
| First SIGINT | Normal | Same as `q` |
| Second SIGINT | Sync modal visible | Force-quit immediately |
| `q` key | Intel not configured | Exit immediately (no modal) |
| First SIGINT | Intel not configured | Exit immediately (no modal) |
