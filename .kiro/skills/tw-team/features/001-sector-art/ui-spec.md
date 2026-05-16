# UI Spec: Sector Art Panel

## Interface
HUD section + CLI command

## Information Priority
1. Sector contents at a glance (port, planet, stardock presence) — always visible when panel has space
2. Port visual identity (unique per port name) — distinguishes locations
3. Ambient atmosphere (starfield) — fills empty space, sets mood

## Layout

### HUD Art Panel

```
═══════════════════ TW2002 GUIDANCE COMPUTER ═══════════════════
Sector: 865  │  Turns: 247  │  Credits: 12,500
─── CARGO ───                │ ─── BEST PAIRS [t=nearest] ───
 Fuel Ore   x 20 @ 31.5/u   │  [865]↔[246] 3/3 SSB|BBS
 Equipment  x 10 @ 105.0/u  │  [102]↔[103] 2/3 SBS|BSB
 Invested: 1,680 cr          │  [440]↔[441] 2/3 BSS|SBB
 Holds: 38 empty             │
─── SELL NEARBY ───          │ ─── COMMS ───
 [246] Port Alpha (1h) F,E   │  [R] Trader1: anyone at SD?
                             │  [F] Admin: server reset 10pm
─────────────────────────────────────────────────────────────────
·        ╔─────╗     ·                          *         ·
    *   ╔║▓█▓█║╗         ╥╥        .
│││││  ╔║═══▪══║╗      ╔═╩╩═╗              ·
░░░░░░╔║░░╝<>╚░░║╗    ╔╣▪▪▪▪╠╗    +
~~%#○░╔║▓█═══▓█▓║╗   ═╣░░░░░░╠═
≈≈▒~≈░╚═══════════╝    ╚╣▪▪▪▪╠╝         *
○~#∙○░░│                 ╚════╝
≈○~%░░││    .       *      ╨╨                    ·
 [q] quit  [t] toggle pairs
```

Dimensions: full terminal width × remaining rows below two-column area (typically 8–15 rows on 25–35 row terminals).

### Height Allocation Rule
- Two-column area has a fixed height of 12 rows (below header).
- COMMS is the flex element within that fixed height — it gets whatever rows remain after Cargo, Sell Nearby, and Trade Pairs.
- Art panel gets all remaining rows between the two-column area and the footer.
- Minimum art panel height: 6 rows. If fewer than 6 rows available, hide the panel entirely.

### Composition Layers (back to front)
1. **Starfield** — sparse `· * . +` characters, ~2% cell density
2. **Planet** — quarter-circle bottom-left, textured fill with atmosphere limb
3. **Port** — WFC-generated structure, centered (offset right if planet present)
4. **Stardock** — static design, right 3/4, slightly above center

### Graceful Degradation
- Terminal < 25 rows: art panel hidden entirely, existing layout unchanged
- Terminal 25–29 rows: art panel gets 6–10 rows (smaller port art)
- Terminal ≥ 30 rows: full art panel (12–15 rows)
- COMMS section adapts to reduced space (already handles variable height)

## Color Scheme
- **Starfield**: dim grays/whites (color 238–255) — subtle, doesn't compete
- **Planet surface**: blues (27, 33, 39), greens (22, 28, 34), browns (94, 100, 136) — terrain texture
- **Planet limb**: bright cyan (51, 45) — atmosphere glow, draws the eye to the edge
- **Port hull/frame**: base hue from seed (dominant, 60% of port pixels) — station identity
- **Port accents**: complementary colors per tile category — visual interest without chaos
- **Stardock**: neutral grays (240, 245, 250) + blue windows (39) — distant, understated

## Update Triggers
- **Sector change**: art regenerated and cached when player warps to a new sector
- **HUD refresh (250ms)**: redraws cached art (no regeneration, no flicker)
- **Terminal resize**: art regenerated at new dimensions

## States
- **Normal (port + planet + stardock)**: full composed scene
- **Port only**: starfield + port art centered
- **Planet only**: starfield + planet (no port in this sector)
- **Empty sector**: starfield only — sparse stars on black
- **Small terminal**: panel hidden, no art shown

## CLI Syntax
```
tw sector-art <sector_id>
```

### Output Format
Renders the composed sector art to stdout with ANSI 256-color. Same visual as the HUD panel but at a fixed 80×14 canvas size.

```
$ tw sector-art 865
─── Sector 865: The Federation ───
·        ╔─────╗     ·                          *         ·
    *   ╔║▓█▓█║╗         ╥╥        .
│││││  ╔║═══▪══║╗      ╔═╩╩═╗              ·
...
```

Errors if sector hasn't been visited: `Error: Sector 865 has not been explored yet.`

## Data Requirements
- Sector explored status (existing: `get_sector()`)
- Port name and class (existing: `get_port()`)
- Planet presence per sector (NEW: needs parser + storage)
- Stardock detection via port_class == 0 (existing)

## Interaction Notes
- No user interaction with the art panel — it's purely informational
- Art is static between sector changes (cached)
- No scrolling, no selection, no cursor in the art area
- Existing keybindings unchanged: `q` quit, `t` toggle pairs
