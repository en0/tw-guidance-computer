# Design Review — PM Adversary

## Verdict: PASS (with notes)

## Use Case Fidelity

All 8 user use cases are present verbatim in the "Use Cases" section. None dropped, merged, or reinterpreted. ✓

## Use Case Coverage

| UC | Covered By | Verdict |
|----|-----------|---------|
| 1 | WFC algorithm seeded by SHA-256 of port name; deterministic across players | ✓ |
| 2 | Starfield background always present; empty sectors show only starfield | ✓ |
| 3 | Quarter-circle planet bottom-left, static design | ✓ |
| 4 | Static stardock graphic, right-of-center, slightly elevated, smaller (conveys distance) | ✓ |
| 5 | Composition layers defined: planet bottom-left, port center, stardock right | ✓ |
| 6 | "Planet art is a single static design, reused everywhere" | ✓ |
| 7 | "Stardock art is a single static design" | ✓ |
| 8 | CLI command `tw sector-art <sector_id>`, errors if unexplored | ✓ |

## Issues Found

### Issue 1: Planet display format is documented incorrectly (LOW)

The Data Requirements section states:
```
Planets : <name> (<class>)
```

But the actual observed format (confirmed in `knowledge/parser-patterns/planet-display.md` from real session data) is:
```
Planets : (M) Terra
```

That's `(class) name`, not `name (class)`. The TW Expert Notes section repeats this same incorrect format. This doesn't affect the use cases or success criteria — the intent (detect planets) is correct — but it's a factual error in the design document that could mislead a builder who reads only the design and not the parser-patterns knowledge base.

**Impact**: Low. The impl plan already has the correct regex. But the design doc should be corrected.

### Issue 2: Stardock + Port dual representation could use clarification (INFORMATIONAL)

A stardock IS a port (class 0). The design correctly identifies this. UC#5 explicitly says "port in the middle, stardock on the right" — so a stardock sector shows BOTH generated port art AND the static stardock graphic. This is the user's stated intent and is handled correctly. Just noting that this means a stardock sector is the most visually busy scene (starfield + port art + stardock art, possibly + planet).

### Issue 3: Success criterion #9 has no use case trace (INFORMATIONAL)

"Art updates when the player moves to a new sector (triggered by sector change detection)" — this is an implementation behavior, not a user-stated use case. It's implied by all the "when I arrive at" use cases but isn't explicitly traced. Not a problem, just noting the asymmetry.

## Scope Check

No scope creep detected. The WFC algorithm description is detailed but references an existing PoC (`tools/station_gen.py`), so it's documenting a known approach rather than inventing scope.

## Data Availability

- Port name: ✓ (existing `get_port()`)
- Planet presence: Correctly identified as needing new parser work
- Stardock: ✓ (existing port_class == 0)
- Sector explored status for CLI: ✓ (existing `get_sector()`)

## Player Utility

This is ambient/atmospheric rather than decision-support. It doesn't help with trading decisions directly. However, it gives visual identity to sectors (spatial memory aid) and communicates sector contents at a glance without reading text. The CLI recall command has clear utility for planning routes to remembered locations. Reasonable value for the screen real estate consumed.
