# Design Review — PM Adversary

## Verdict: PASS (with notes)

## Use Case Fidelity

All 9 user use cases are present verbatim in the "Use Cases" section. None dropped, merged, or reinterpreted. ✓

## Use Case Coverage

| UC | Requirement | Design Coverage | Status |
|----|-------------|----------------|--------|
| 1 | Warp edges ONLY from sector display block, never from nav menus | Nav Menu Exclusion section defines prefix detection `(T)`, `(S)`, `(*)`, `(\d)`. Pattern 2 is the only warp source. | ✓ |
| 2 | Visiting a sector replaces ALL existing warp edges from that sector (self-healing) | Self-Healing Warps section: DELETE all warps WHERE `from_sector = N` (regardless of source), then INSERT observed set. | ✓ |
| 3 | Intel import replaces warps per-sector (not additive) when newer | Intel Import section: compare `updated_at`, if imported newer → DELETE + INSERT. If local newer or equal → skip. | ✓ |
| 4 | Current sector from command prompt AND sector display block | Pattern 1 (command prompt) and Pattern 2 (sector display) both set current sector. | ✓ |
| 5 | Turns from two specific patterns only | Pattern 3 lists both: `You have N turns this Stardate.` and `One turn deducted, N turns left.` | ✓ |
| 6 | Credits from two on-hand patterns only (bank ignored) | Pattern 4 lists both: `You have N credits.` and `You have N credits and N empty cargo holds.` Bank explicitly ignored. | ✓ |
| 7 | Status bar as force-resync for sector, turns, credits | Pattern 5 defines status bar parsing setting all three values. | ✓ |
| 8 | Cargo tracking removed — return empty cargo | "Cargo-related queries return empty data; display layers show 'Empty'" in success criteria. Storage section: `cargo_json` will be `[]`. | ✓ |
| 9 | Nav menu must never be parsed as authoritative data | Nav Menu Exclusion section with examples. Success criterion: "No false warp edges created when nav menu is displayed." | ✓ |

## Issues Found

### Issue 1: Nav menu exclusion mechanism is under-specified (MEDIUM)

The design says the `(T)`, `(S)`, `(*)`, `(\d)` prefix "distinguishes them from real sector displays." But it doesn't specify the MECHANISM for exclusion. Two approaches exist:

1. **Negative lookahead**: Modify the sector regex to NOT match lines preceded by these prefixes.
2. **Pre-filtering**: Strip or skip lines matching the nav menu pattern before running sector extraction.
3. **Context tracking**: Track whether the parser is "inside" a nav menu display and suppress parsing.

The current parser (confirmed by reading `parse_log_chunk.py`) uses `sector_re = re.compile(r"Sector\s+:\s+(\d+)\s+in\s+(.+?)\.")` which matches nav menu lines because they have the same format. The design correctly identifies the problem but leaves the solution mechanism to the architect.

Additionally, the nav menu example shows indented lines:
```
(T) Sector  : 1 in The Federation.
    Ports   : Sol, Class 0 (Special)
```

The `Ports` line is indented with 4 spaces. The current port regex `r"Ports\s+:\s+(.+?),\s+Class\s+(\d+)\s+\(([^)]+)\)"` would match this indented line. The design says nav menu lines "must NOT trigger sector/port/warp parsing" but only explicitly discusses the `Sector` line prefix detection. The indented `Ports` and `Planets` lines under nav menu entries also need exclusion — they don't have the `(T)` prefix themselves.

**Impact**: Medium. The architect needs to decide the mechanism. The indented port/planet lines are a subtlety that could be missed if the exclusion only checks for the `(T)` prefix on the `Sector` line.

### Issue 2: Design removes turn patterns that exist in the current parser (INFORMATIONAL)

UC#5 says turns are derived "only from" two patterns. The current parser (`_extract_player_state`) also handles:
- `You don't have any turns left` → sets turns to 0
- `You recover N of your turns` → adds N to current turns

The design's Pattern 3 lists only:
- `You have N turns this Stardate.`
- `One turn deducted, N turns left.`

The "zero turns" and "recover turns" patterns are being dropped. This is a deliberate simplification per the user's stated UC#5 — the user explicitly listed only two patterns. However, dropping "You don't have any turns left" means if the player runs out of turns, the parser won't detect it until the next absolute-value pattern fires.

**Impact**: Informational. The user explicitly stated which patterns to keep. The design is faithful to the UC. The "zero turns" case is an edge case that will self-correct on the next `One turn deducted, 0 turns left.` or status bar resync.

### Issue 3: Intel import warp strategy change affects Feature 004 compatibility (LOW)

The design correctly identifies this dependency: "Feature 004 (Shared Intel): import strategy change must be compatible with existing export/CSV format."

The CSV format (confirmed in `intel_csv.py`) exports warps as individual rows:
```
from_sector,to_sector,explored,updated_at
```

The current `import_warps` uses `INSERT OR IGNORE` per row. The new strategy needs to:
1. Group imported warps by `from_sector`
2. For each sector group, compare timestamps against local
3. If newer, delete local warps for that sector and insert the imported set

This is a change to `import_warps` in `SqliteGameStateStore` — the CSV format itself doesn't change. The design correctly identifies this as a dependency but doesn't specify whether the `IntelStore` port signature changes or just the implementation.

**Impact**: Low. The CSV format is unchanged. The port method signature (`import_warps(warps, source) -> int`) can remain the same — only the internal strategy changes. The architect will handle this.

### Issue 4: "Cargo tracking is removed" — what about the `<Info>` sync point? (LOW)

The current parser extracts cargo from `<Info>` blocks and status bars as part of sync points. UC#8 says cargo tracking is removed and the system returns empty cargo. But the design's Pattern 5 (status bar) still shows `Ore 0│Org 0│Equ 0│Col 0` fields being parsed.

The design says `cargo_json` will be `[]`. But does the parser still PARSE the cargo fields from the status bar (and just not store them)? Or does it skip them entirely? The status bar regex currently captures Ore/Org/Equ/Col groups.

For UC#7, the status bar only needs to resync sector, turns, and credits. The cargo fields in the status bar can be ignored entirely. The design is consistent here — Pattern 5 says "Sets sector=3, turns=880, credits=753" with no mention of cargo. But the existing regex captures more fields. The architect needs to decide whether to simplify the regex or just ignore the extra captures.

**Impact**: Low. The design's intent is clear (cargo is dead). Implementation detail for the architect.

### Issue 5: Commerce report removal — existing port data enrichment lost (INFORMATIONAL)

The design removes `_extract_commerce_reports`. Currently, commerce reports provide detailed commodity quantities and percentages that enrich port data beyond what the sector display provides. The sector display only gives name, class, and type code. Commerce reports add `PortCommodity` objects with quantity and pct.

UC#8 removes cargo tracking, and the design's "Out of Scope" says "New parser patterns beyond the 5 defined above" are excluded. Commerce reports are not in the 5 patterns. This is a deliberate scope reduction.

However, the `FindTradePairs` use case and CLI `tw ports` command currently display commodity quantities from commerce reports. After this change, ports will only have name/class/type — no quantities. This doesn't break anything (the display handles missing commodities gracefully), but it's a capability reduction not explicitly called out.

**Impact**: Informational. The user's UCs don't mention commerce reports. The design is faithful to what was asked. The capability loss is a natural consequence of the simplification.

### Issue 6: Chat removal not in any UC (INFORMATIONAL)

The design's "Changes Needed" section says "Parser: remove commerce reports, transactions, haggling, chat." Chat removal is listed in "Out of Scope" as well. But none of the 9 UCs mention chat. The design is removing chat parsing as part of the simplification, which is reasonable (the design says "simplified parser focused on the 5 essential patterns"), but it's scope that goes slightly beyond what the UCs explicitly request.

The user said "Nav menu must never be parsed" and listed 5 specific patterns to keep. Chat is not in those 5 patterns, so removing it is consistent with the "exhaustive list" framing. Not a violation — just noting it's an implicit removal rather than an explicit UC.

**Impact**: Informational. Consistent with the "5 essential patterns" framing. Not scope creep — it's scope reduction.

## Success Criteria Testability

| Criterion | Testable? | How |
|-----------|-----------|-----|
| Warps ONLY from sector display blocks | ✓ | Feed nav menu text through parser, verify no warps created |
| Visiting sector deletes + inserts warps | ✓ | Pre-populate warps, parse sector display, verify old warps gone and new set present |
| Intel import replaces per-sector when newer | ✓ | Import warps with newer timestamp, verify old warps replaced |
| Current sector from prompt and display | ✓ | Parse both patterns, verify sector updates |
| Turns from two patterns only | ✓ | Parse each pattern, verify turns set; parse other turn text, verify no change |
| Credits from two patterns only | ✓ | Parse each pattern, verify credits set; parse bank pattern, verify no change |
| Status bar resyncs sector/turns/credits | ✓ | Parse status bar, verify all three values updated |
| Cargo returns empty | ✓ | Query cargo after any parse, verify empty list |
| No false warps from nav menu | ✓ | Parse full nav menu display, verify zero warp insertions |

All criteria are measurable and testable. ✓

## Data Availability

| Data | Available? | Source |
|------|-----------|--------|
| Sector display block | ✓ | Existing regex, observed in session logs |
| Command prompt | ✓ | Existing regex, observed in session logs |
| Nav menu format | ✓ | Documented in knowledge base (`parser-patterns/`) |
| Turn patterns | ✓ | Existing regex in parser |
| Credit patterns | ✓ | Existing regex in parser |
| Status bar | ✓ | Existing regex in parser |
| Warp connections from sector display | ✓ | Existing extraction logic |
| `replace_warps_from_sector` store method | ❌ | New — needs to be added to `GameStateWriter` port |
| Intel warp replacement logic | ❌ | New — `import_warps` strategy change needed |

All required data is available in the session log. The two "new" items are store/adapter changes, not data availability issues. ✓

## Scope Check

The design REMOVES scope (commerce reports, transactions, haggling, chat, cargo tracking) rather than adding it. The only new behavior is:
1. Nav menu exclusion (directly from UC#1, UC#9)
2. Warp replacement on visit (directly from UC#2)
3. Intel warp replacement strategy (directly from UC#3)

No scope creep detected. The design is a net simplification. ✓

## Dependency Check

Feature 004 (Shared Intel) is correctly identified as a dependency. The warp import strategy change must not break the existing CSV format or the `PullIntel` → `ImportIntel` → `import_warps` pipeline. Confirmed: the CSV format is row-per-warp and doesn't change. Only the merge strategy inside `import_warps` changes.

## Summary

The design is faithful to all 9 use cases, well-scoped (net reduction in complexity), and all success criteria are testable. The one medium issue (nav menu exclusion mechanism under-specification, particularly for indented port/planet lines) is an implementation detail the architect will resolve — it doesn't represent a design gap or UC violation. The design correctly identifies the problem, the solution intent, and the constraints.
