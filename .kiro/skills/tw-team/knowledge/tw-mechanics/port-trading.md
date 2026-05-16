# Port Types and Trading

## How It Works
Ports trade three commodities: Fuel Ore, Organics, Equipment. Each port has a "class" (1-8) that determines which commodities it buys and sells.

| Class | Fuel Ore | Organics | Equipment | Type Code |
|-------|----------|----------|-----------|-----------|
| 1 | Buy | Buy | Buy | BBB |
| 2 | Buy | Buy | Sell | BBS |
| 3 | Buy | Sell | Buy | BSB |
| 4 | Buy | Sell | Sell | BSS |
| 5 | Sell | Buy | Buy | SBB |
| 6 | Sell | Buy | Sell | SBS |
| 7 | Sell | Sell | Buy | SSB |
| 8 | Sell | Sell | Sell | SSS |

Special ports:
- Class 0 / "Special" — StarDock, Class 0 ports (sector 1, etc.)
- Class 9 — Sometimes referenced but not standard

## Trade Pairs
Two adjacent ports are a "trade pair" if they have complementary buy/sell on at least one commodity. Best pairs complement on 2+ commodities (e.g., BBS ↔ SSB = 3-way complement).

## What the Player Sees
Port display in sector:
```
Ports   : Trader Vic's, Class 6 (SBS)
```

Commerce report (from `I` command at port):
```
Commerce report for Trader Vic's: 12:34:56
Fuel Ore   Selling    500   100%
Organics   Buying     300    50%
Equipment  Selling    200    75%
```

## Relevant to Parser?
Yes — both the sector port display and commerce reports are parsed. The type code and commodity details are extracted.

## Sources
Observed in session logs. Standard TW2002 mechanics.
