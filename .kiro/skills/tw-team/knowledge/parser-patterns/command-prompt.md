# Command Prompt

## What It Captures
Current sector from the game's command prompt. Used to track player position.

## Raw Example (with ANSI noted)
```
[35mCommand [[33m[1mTL[22m=[1m00:00:00[35m[22m][37m[1m:[35m[22m[[36m[1m616[35m[22m] ([33m[1m?=Help[35m[22m)? :[K[1C[m
```

## Clean Text (after strip)
```
Command [TL=00:00:00]:[616] (?=Help)? :
```

## Regex
```python
prompt_re = re.compile(r"\[(\d+)\]\s*\(\?=Help\)")
```

## Edge Cases
- The time display `TL=00:00:00` is always present
- Sector number is in brackets before `(?=Help)`
- This appears frequently — after every command response
- Can be used as a reliable position tracker between other parse events
