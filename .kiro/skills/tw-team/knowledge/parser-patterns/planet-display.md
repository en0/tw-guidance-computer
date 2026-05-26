# Planet Detection

## What It Captures
Presence of a planet in a sector. Appears in sector display output (both full display and navigation route display).

## Raw Example (with ANSI noted)
```
\x1b[35mPlanets \x1b[33m\x1b[1m: \x1b[32m\x1b[22m(\x1b[33m\x1b[1mM\x1b[32m\x1b[22m) Terra\x1b[K\r\x1b[m
```

Indented variant (in route display):
```
    \x1b[35mPlanets \x1b[33m\x1b[1m: \x1b[32m\x1b[22m(\x1b[33m\x1b[1mM\x1b[32m\x1b[22m) es\x1b[K\r\x1b[m
```

## Clean Text (after ANSI strip)
```
Planets : (M) Terra
    Planets : (M) es
    Planets : (K) vortex
    Planets : (O) Mando-2
```

## Context in Sector Display
The `Planets` line appears after the `Ports` line in a sector display block:
```
(T) Sector  : 1 in The Federation.
    Ports   : Sol, Class 0 (Special)
    Planets : (M) Terra
(S) Sector  : 214 in The Federation.
```

Or in a full sector display:
```
Sector  : 616 in uncharted space.
Ports   : Trader Vic's, Class 6 (SBS)
Planets : (M) es
Warps to Sector(s) :  (544) - (564) - (825)
```

## Regex
```python
planet_re = re.compile(r"Planets?\s*:\s*\(([A-Z])\)\s*(.+)")
```

Captures:
- Group 1: Planet class letter (M, K, O, etc.)
- Group 2: Planet name

## Association with Sector
The planet line always appears within a sector display block. The parser should associate it with the most recently parsed sector ID (same approach used for port detection).

## What We Need for Feature 001
Boolean presence only — "this sector has a planet." The class and name are captured for future use but the art feature only checks `has_planet: bool`.

## Edge Cases
- Multiple planets per sector: TW2002 supports this but it's rare. The regex will match each line. For art purposes, one match = has_planet = True.
- Planet names can contain hyphens and numbers: "Mando-2", "es", "Terra", "vortex"
- Planet class is always a single uppercase letter in parentheses: (M), (K), (O), (H), (L), (U)
- The line may be indented (4 spaces) in route/navigation display vs. flush-left in full sector display
- The `Planets` keyword may appear as `Planet` (singular) in some contexts — regex handles both with `Planets?`

## Storage
New table: `planets`
```sql
CREATE TABLE IF NOT EXISTS planets (
    sector_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    planet_class TEXT NOT NULL,
    PRIMARY KEY (sector_id, name)
);
```

Query for art: `SELECT 1 FROM planets WHERE sector_id = ? LIMIT 1` → boolean presence.

## Sources
Observed in `~/Documents/Games/TradeWars/sessions/init-session.log`. Multiple examples across different sectors.
