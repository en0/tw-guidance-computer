# Feature Design: Parser Reset

STATUS: complete

## Use Cases (from user — do not modify)
1. The parser should derive warp edges ONLY from the sector display block (`Sector : N in region.` followed by `Warps to Sector(s) :`), never from nav menus or other contexts.
2. When I visit a sector, the system replaces ALL existing warp edges from that sector (regardless of source) with the complete set just observed — self-healing bad data.
3. When importing intel, warps for a sector are replaced as a complete set (not additive) if the imported timestamp is newer than local.
4. Current sector is derived from the command prompt `Command [TL=...]:[N] (?=Help)? :` and from the sector display block (both are authoritative).
5. Turn count is derived only from `You have N turns this Stardate.` and `One turn deducted, N turns left.`
6. Credits on-hand are derived only from `You have N credits.` and `You have N credits and N empty cargo holds.` — bank account is ignored.
7. The compressed status bar (`Sect N│Turns N│Creds N│...`) serves as a force-resync for sector, turns, and credits when the player opens it.
8. Cargo tracking is removed — the system returns empty cargo so existing display layers show "Empty" without code changes.
9. The nav menu (`(T) Sector :`, `(S) Sector :`, `(*) Sector :`, `(N) Sector :`) must never be parsed as authoritative sector/port/warp data.

## Problem
The parser currently matches `Sector :` and `Warps to Sector(s) :` patterns too broadly. The nav menu (saved sector locations) uses the same display format as real sector arrivals, causing the parser to create false warp edges. These false edges propagate into trade pair calculations, showing pairs as 1-hop apart that aren't actually adjacent. Additionally, the parser has accumulated complexity (commerce reports, haggling, cargo cost basis, transaction tracking) for features that provide little value. A simplified parser focused on the 5 essential patterns is more reliable and maintainable.

## Success Criteria
- [ ] Warp edges are ONLY created from sector display blocks, never from nav menu context ← UC#1, UC#9
- [ ] Visiting a sector deletes all prior warps from that sector and inserts the observed set ← UC#2
- [ ] Intel import replaces warps per-sector (not additive) when imported timestamp is newer ← UC#3
- [ ] Current sector updates from both command prompt and sector display block ← UC#4
- [ ] Turn count updates only from the two absolute-value patterns ← UC#5
- [ ] Credits update only from the two on-hand patterns (bank ignored) ← UC#6
- [ ] Status bar parsing resyncs sector, turns, and credits ← UC#7
- [ ] Cargo-related queries return empty data; display layers show "Empty" ← UC#8
- [ ] No false warp edges created when nav menu is displayed in session ← UC#9

## User-Facing Behavior

### Parser Patterns (exhaustive list)

**Pattern 1 — Command Prompt (current sector):**
```
Command [TL=00:00:00]:[214] (?=Help)? :
```
Sets current sector to 214.

**Pattern 2 — Sector Display Block (sector info + warps + current sector):**
```
Sector  : 272 in Gastonbury.
Ports   : Hornet II, Class 5 (SBS)
Warps to Sector(s) :  51 - (203) - (224) - 342 - 860
```
- Sets current sector to 272
- Records sector 272 with region "Gastonbury", explored=true
- Records port "Hornet II" class 5 type "SBS" at sector 272
- Records planets if present
- **Deletes** all existing warps FROM sector 272 (any source)
- Inserts warps: 272→51, 272→203, 272→224, 272→342, 272→860
- Sectors in `()` are unexplored; bare numbers are explored

**Pattern 3 — Turns (absolute set):**
```
You have 47 turns this Stardate.
```
```
One turn deducted, 813 turns left.
```
Both set turns to the stated value.

**Pattern 4 — Credits (on-hand):**
```
You have 272 credits.
```
```
You have 272 credits and 1 empty cargo holds.
```
Sets credits to 272. The bank pattern (`credits in your account`) is ignored.

**Pattern 5 — Status Bar (force resync):**
```
Sect 3│Turns 880│Creds 753│Figs 1│Shlds 30│Hlds 1│Ore 0│Org 0│Equ 0│Col 0
```
Sets sector=3, turns=880, credits=753. Serves as recalibration if parser drifted.

### Nav Menu Exclusion

The nav menu displays saved sector locations with markers:
```
(T) Sector  : 1 in The Federation.
    Ports   : Sol, Class 0 (Special)
(S) Sector  : 214 in The Federation.
(1) Sector  : 178 (Not Scanning)
(2) Sector  : 749 in uncharted space.
    Ports   : Nog II, Class 2 (BSB)
(*) Sector  : 178 in uncharted space.
```
These lines must NOT trigger sector/port/warp parsing. The `(T)`, `(S)`, `(*)`, `(\d)` prefix distinguishes them from real sector displays.

### Self-Healing Warps

When the parser sees a sector display block with `Warps to Sector(s)`:
1. DELETE all rows in `warps` table where `from_sector = N` (regardless of `source`)
2. INSERT the new complete set

This ensures:
- False edges from the nav menu bug are corrected on next visit
- Imported intel edges are corrected when you visit the sector yourself
- The warp graph is always consistent with the most recent observation

### Intel Import — Warp Strategy Change

Current: `INSERT OR IGNORE` (additive — never removes edges)
New: **Replace per-sector if newer**

When importing warps for sector N from a corp mate:
- Compare imported `updated_at` vs max `updated_at` of local warps from sector N
- If imported is newer: DELETE all warps from sector N, INSERT imported set
- If local is newer or equal: skip

This ensures false edges don't persist through intel sync.

## Data Requirements

### Already Available
- Command prompt regex (existing)
- Sector display regex (existing, needs tightening)
- Warp extraction (existing, needs re-association logic)
- Port extraction from sector display (existing)
- Planet extraction from sector display (existing)
- Status bar regex (existing)
- Turn count patterns (existing)
- Credit patterns (existing)

### Changes Needed
- Store: `replace_warps_from_sector(sector_id, warps)` — delete + insert
- Store: cargo queries return empty
- Intel import: warp strategy from additive to replace-per-sector
- Parser: nav menu exclusion logic
- Parser: remove commerce reports, transactions, haggling, chat

### Storage
- No new tables or columns
- Existing `warps` table used with delete+insert pattern
- `cargo_json` in `player_status` will be `[]`

## Dependencies
- Feature 004 (Shared Intel): import strategy change must be compatible with existing export/CSV format

## Out of Scope
- HUD redesign (cargo/sell sections will show "Empty" naturally)
- CLI command removal (commands still work, just show no cargo)
- New parser patterns beyond the 5 defined above
- Chat parsing

## Open Questions
None — all resolved during discussion.

## TW Expert Notes
- `Warps to Sector(s)` always shows the COMPLETE set of edges from a sector. There is no partial display.
- The nav menu is accessed via `N` command. Entries are prefixed with `(T)` (Trade), `(S)` (StarDock), `(*)` (current sector), or `(1-9)` (user-saved).
- Warps in TW2002 are bidirectional by default. One-way warps exist but are rare.
- The status bar is shown via `/` command. It's on-demand, not automatic.
