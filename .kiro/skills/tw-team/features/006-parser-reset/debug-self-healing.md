# Parser Debug: Sector 860 Self-Healing Not Working

## Problem

After the parser rewrite, self-healing warps don't work. User visited both sector 17 and sector 860 with the new code running. DB still shows false warps:

```
[(860, 17), (860, 860)]
```

These should have been replaced when visiting sector 860.

## What We Know

The raw session data (line 2361 of `tw-session-20260523-190427.log`) shows that during auto-warp, the game output for consecutive sectors gets concatenated onto single file lines via cursor positioning (`\x1b[row;colH`). After ANSI stripping, `\r` characters from the progress bar separate segments.

## Changes Already Made (not yet committed)

1. `text.split("\n")` → `text.splitlines()` — splits on `\r` too, so sector displays after progress bars get their own line
2. `_WARP_RE` changed from `(.+?)(?:$|\n)` to `([\d\s\-()]+)` — captures only warp-formatted chars, stops at any letter

## Suspected Additional Issue

The inner loop in `_extract_sector_displays` checks break conditions BEFORE checking for warps:

```python
while i < len(lines):
    sub = lines[i]
    if _NAV_PREFIX_RE.match(sub) or _SECTOR_RE.search(sub) or _PROMPT_RE.search(sub):
        break  # ← fires first

    ...
    warp_m = _WARP_RE.search(sub)  # ← never reached
```

After ANSI stripping, the warp line may contain the command prompt on the same line:
```
Warps to Sector(s) :  51 - 272 - 300 - (812)Command [TL=00:00:00]:[860] (?=Help)? :
```

`_PROMPT_RE` (`\[(\d+)\]\s*\(\?=Help\)`) would match `[860] (?=Help)` causing the break before warps are processed.

## What Needs To Be Verified

Run this from `/home/ian/src/tw-guidance-computer`:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'src')
from tw_guidance_computer.adapters.outbound.log_reader import strip_ansi
with open('/home/ian/Documents/Games/TradeWars/sessions/tw-session-20260523-190427.log', 'rb') as f: data = f.read()
text = strip_ansi(data.decode('utf-8', errors='replace'))
lines = text.splitlines()
for i, line in enumerate(lines):
    if '860' in line and 'Sector' in line:
        print(f'=== Sector line {i} ==='); print(repr(line[:300])); print()
    if '860' in line and 'Warps to Sector' in line:
        print(f'=== Warp line {i} ==='); print(repr(line[:300])); print()
"
```

This shows what the parser actually sees after stripping and splitlines. From this output we can confirm whether:
1. `Sector : 860` gets its own line (splitlines fix works)
2. The warp line for sector 860 also contains a command prompt (break-before-warp bug)

## Proposed Fix (pending verification)

Move the warp check ABOVE the break condition in the inner loop:

```python
while i < len(lines):
    sub = lines[i]

    # Check warps first — warp line may also contain a prompt after ANSI strip
    warp_m = _WARP_RE.search(sub)
    if warp_m:
        self._process_warps(sector_id, warp_m.group(1))
        i += 1
        break

    if _NAV_PREFIX_RE.match(sub) or _SECTOR_RE.search(sub) or _PROMPT_RE.search(sub):
        break

    # ... port/planet checks unchanged
```

## Files

- Parser: `src/tw_guidance_computer/application/parse_log_chunk.py`
- Log reader (strip_ansi): `src/tw_guidance_computer/adapters/outbound/log_reader.py`
- Session: `/home/ian/Documents/Games/TradeWars/sessions/tw-session-20260523-190427.log`
- DB: `~/.local/share/tw-guidance-computer/game.db`
