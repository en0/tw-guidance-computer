# Sector Display

## What It Captures
Current sector ID, region name, and warp connections to adjacent sectors.

## Raw Example (with ANSI noted)
```
[32m[1mSector  [33m: [36m616 [32m[22min [34muncharted space.[K[m
[32m[1mWarps to Sector(s) [33m:  [35m[22m([31m[1m544[35m[22m) [32m- [35m([31m[1m564[35m[22m) [32m- [35m([31m[1m825[35m[22m)[K[m
```

## Clean Text (after strip)
```
Sector  : 616 in uncharted space.
Warps to Sector(s) :  (544) - (564) - (825)
```

## Regex
```python
sector_re = re.compile(r"Sector\s+:\s+(\d+)\s+in\s+(.+?)\.")
warp_re = re.compile(r"Warps to Sector\(s\)\s*:\s*(.+?)(?:Stop|Auto|Command|\n|$)")
```

Warp sector extraction: `re.findall(r"\d+", warp_text)` for all sectors.
Unexplored sectors are in parentheses: `re.findall(r"\((\d+)\)", warp_text)`.

## Edge Cases
- Region can be "uncharted space", "The Federation", "The Frontier", etc.
- Region may have trailing "(unexplored)" or "(Not Scanning)" — stripped by parser
- Warp list can be terminated by various strings (Stop, Auto, Command, newline)
- Sector numbers in parentheses `(544)` indicate unexplored warps
- Bare numbers `544` indicate explored warps
