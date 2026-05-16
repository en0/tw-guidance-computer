# Data Flow

How the system connects end-to-end, from game session to user-facing output.

## Three-Terminal Workflow

```
Terminal 1 (Game)          Terminal 2 (HUD)           Terminal 3 (CLI)
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ script -f log    │      │ tw-hud log       │      │ tw pairs         │
│ ssh tw2002       │      │   --parse-existing│      │ tw path 865 246  │
│                  │      │                  │      │ tw sell           │
│ [playing game]   │      │ [live display]   │      │ [ad-hoc queries] │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                          │
         │ writes                  │ tails                    │ reads
         ▼                         ▼                          ▼
    session.log ──────────> TailLogReader ──────> SQLite DB <── SqliteGameStateStore
                            (ANSI strip)          (WAL mode)
```

## Pipeline Stages

### 1. Capture: `script -f <logfile>`

- Player runs `script -f ~/tradewars/sessions/session.log` then SSHs to the game
- `script` records raw terminal output including all ANSI escape codes
- `-f` flag flushes after each write (essential for real-time tailing)
- The log file grows continuously during gameplay

### 2. Read: TailLogReader (adapter)

- Opens log file, seeks to end (or beginning with `--parse-existing`)
- On each tick, reads new bytes since last offset
- Strips ANSI escape sequences and control characters
- Returns clean text to the parser
- Regex: removes `\x1b[...X` sequences, OSC sequences, charset switches, control chars

### 3. Parse: ParseLogChunk (use case)

- Receives clean text chunks
- Stateful — maintains running player state across calls
- Extracts in order:
  1. Sectors and warp connections
  2. Port headers (name, class, type)
  3. Commerce reports (detailed commodity data)
  4. Sync points (resets cargo state from authoritative source)
  5. Player state (turns, credits, holds)
  6. Transactions (buy/sell with cost basis) — only after last sync point
  7. Chat messages
- Writes everything to the store

### 4. Store: SqliteGameStateStore (adapter)

- SQLite database at `~/.local/share/tw-guidance-computer/game.db`
- WAL mode — allows concurrent reads while HUD writes
- Tables: sectors, ports, port_commodities, warps, player_status, chat_messages
- Upsert semantics — new data overwrites old for sectors/ports/warps
- Persists across sessions — knowledge accumulates

### 5. Display: HudDisplay (adapter) or CliAdapter (adapter)

- HUD: curses TUI, 250ms refresh loop, reads from store each tick
- CLI: one-shot queries, reads from store, prints to stdout, exits

## Key Design Decisions

- **ANSI stripping in adapter, not parser**: The log reader handles the I/O concern of translating raw bytes. The parser only sees clean text.
- **Stateful parser**: Game state is cumulative. Sector display tells you where you are, but cargo persists until a transaction. Parser tracks running state.
- **Sync points reset cargo**: `<Info>` blocks and status bars are authoritative snapshots. Transactions are only processed after the last sync point in a chunk to avoid double-counting.
- **WAL mode**: The HUD writes continuously. The CLI reads on-demand. WAL prevents locking conflicts.
- **Cost basis via weighted average**: When buying more of a commodity already held, the cost_per_unit is recalculated as a weighted average.

## File Locations

| Component | Path |
|-----------|------|
| Session logs | `~/tradewars/sessions/` |
| Database | `~/.local/share/tw-guidance-computer/game.db` |
| HUD entry point | `src/tw_guidance_computer/hud.py` |
| CLI entry point | `src/tw_guidance_computer/cli.py` |
| Parser | `src/tw_guidance_computer/application/parse_log_chunk.py` |
| Log reader | `src/tw_guidance_computer/adapters/log_reader.py` |
| SQLite store | `src/tw_guidance_computer/adapters/sqlite_store.py` |
| TUI display | `src/tw_guidance_computer/adapters/tui.py` |
| CLI commands | `src/tw_guidance_computer/adapters/cli_commands.py` |
