# HUD Layout (tw-hud)

Curses-based real-time TUI. Runs in its own terminal alongside the game session.

## Overall Structure

```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500
─── CARGO ───                │ ─── BEST PAIRS [t=nearest] ───
 Fuel Ore   x 20 @ 31.5/u   │  [865]↔[246] 3/3 SSB|BBS
 Equipment  x 10 @ 105.0/u  │  [102]↔[103] 2/3 SBS|BSB
 Invested: 1,680 cr          │  [440]↔[441] 2/3 BSS|SBB
 Holds: 38 empty             │
─── SELL NEARBY ───          │
 [246] Port Alpha (1h) F,E   │ ─── COMMS ───
 [301] Port Beta (3h) E      │  [R] Trader1: anyone at SD?
                             │  [F] Admin: server reset 10pm
 [q] quit  [t] toggle pairs
```

## Layout

- **Two-panel split**: screen divided at `max_x // 2`
- **Left panel**: CARGO section, then SELL NEARBY section
- **Right panel**: TRADE PAIRS section, then COMMS section
- **Header**: row 0 (title), row 1 (status bar)
- **Footer**: last row, reverse-video keybinding hints

## Header (rows 0–1)

- Row 0: `═` line full width (cyan), centered title "TW2002 GUIDANCE COMPUTER" (cyan bold)
- Row 1: `Sector: N  │  Turns: N  │  Credits: N,NNN` (yellow bold)
- Turn warnings:
  - `< 100` turns: yellow bold + reverse (flashing attention)
  - `< 50` turns: red bold (critical)

## Left Panel

### CARGO Section

- Section header: `─── CARGO ───` (cyan)
- Each cargo line: ` {commodity:<10} x{qty:>3} @ {cost}/u` (green)
- Total investment line if cargo present (yellow)
- Empty holds count (green)
- If no cargo: shows "Empty"

### SELL NEARBY Section

- Section header: `─── SELL NEARBY ───` (cyan)
- Each recommendation: ` [{sector}] {port_name} ({hops}h) buys: {commodities}` (green)
- Shows up to 5 results within 8 hops
- Commodity abbreviations: first letter of each (F, O, E)
- If nothing to sell: "Nothing to sell"
- If no buyers found: "No known buyers nearby" (red)

## Right Panel

### TRADE PAIRS Section

- Section header toggles between:
  - `─── BEST PAIRS [t=nearest] ───` (cyan)
  - `─── NEAREST PAIRS [t=best] ───` (cyan)
- Best mode: sorted by complementary count (3/3 first)
  - ` [{a}]↔[{b}] {count}/3 {type_a}|{type_b}` (green)
- Nearest mode: sorted by hops from current sector
  - ` {hops}h [{a}]↔[{b}] {count}/3 {type_a}|{type_b}` (green)
- Shows up to 6 pairs
- If none found: "None found yet"

### COMMS Section

- Section header: `─── COMMS ───` (magenta)
- Each message: ` [{channel_initial}] {sender}: {message}` (magenta)
- Channel initials: R (radio), F (fed comm-link)
- Shows as many as fit before footer
- Newest at bottom, oldest at top
- If no messages: "No messages"

## Color Scheme (curses pairs)

| Pair | Foreground | Usage |
|------|-----------|-------|
| 1 | Green | Data values, cargo lines, trade pairs |
| 2 | Cyan | Section headers, title bar |
| 3 | Yellow | Status bar values, investment totals |
| 4 | Red | Warnings (low turns, no buyers) |
| 5 | Magenta | COMMS section |

All pairs use default (-1) background.

## Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit HUD |
| `t` | Toggle trade pairs mode (best ↔ nearest) |

## Refresh Behavior

- 250ms main loop (`time.sleep(0.25)`)
- Each tick: read new log data → parse → re-render full screen
- `stdscr.nodelay(True)` — non-blocking input
- `stdscr.erase()` before each render (full redraw)
- `curses.curs_set(0)` — cursor hidden

## Terminal Assumptions

- Minimum usable size: ~100 columns × 20 rows
- No explicit size check — panels just get narrower
- `_safe_addstr` truncates at screen edge, catches curses errors
