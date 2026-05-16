# CLI Commands (tw)

Query tool for the SQLite knowledge base. Separate binary from the HUD — reads the same database.

## Entry Point

`tw <command> [args]` — composition root at `src/tw_guidance_computer/cli.py`

Global option: `--db <path>` (default: `~/.local/share/tw-guidance-computer/game.db`)

## Commands

### tw status

Database summary. No arguments.

```
  Sectors known: 142 (89 explored, 53 seen)
  Ports known: 67
  Warp connections: 312
  Player: sector 865, 247 turns, 12,500 credits
  Port types: {'BBS': 12, 'BSB': 8, 'BSS': 15, 'SBB': 10, 'SBS': 9, 'SSB': 13}
```

### tw sector \<id\>

Show sector info including warps and port details.

```
  Sector 865: The Federation
  Explored: Yes
  Warps: 246 [SSB], 301, 440 [BBS], 102 (?)
  Port: Stardock Alpha - Class 9 (Special)
    Fuel Ore   Selling   2500 (100%)
    Organics   Selling   2500 (100%)
    Equipment  Selling   2500 (100%)
```

Warp annotations: `[TYPE]` if port known, `(?)` if unexplored.

### tw ports [-t TYPE]

List all known ports. Optional type filter (e.g., `-t SSB`).

```
   246: Port Alpha           Class 3 (SSB) F:S2100 O:S1800 E:B900
   301: Port Beta            Class 4 (BBS) F:B1200 O:B800 E:S1500
```

Format: `sector: name  Class N (TYPE) commodity_details`

### tw pairs

Find adjacent trade pairs sorted by complementary count.

```
  [865] Port Alpha (SSB)  <-->  [246] Port Beta (BBS)
  Complementary: 3/3
    buy Fuel Ore at [865], sell at [246]
    buy Organics at [865], sell at [246]
    buy Equipment at [246], sell at [865]
```

### tw path \<start\> \<end\>

BFS shortest path between two sectors.

```
  Path (3 hops): 865 > 246 > 301 > 440
    865: Stardock Alpha (Special)
    246: Port Alpha (SSB)
    440: Port Gamma (BBS)
```

Shows ports along the route. Prints error if no path exists.

### tw search \<pattern\>

Search ports by type code. `*` is wildcard.

```
tw search SS*     # ports selling fuel and organics
tw search *B*     # ports buying organics
tw search BSB     # exact match
```

```
  Ports matching 'SS*':
     246: Port Alpha           (SSB) - The Federation
     440: Port Gamma           (SSS) - Outer Rim
```

### tw nearby \<sector\> [-n HOPS]

Find ports within N hops (default 5) of a sector.

```
  Ports within 5 hops of sector 865:
    1 hops - [246] Port Alpha (SSB)
    2 hops - [301] Port Beta (BBS)
    3 hops - [440] Port Gamma (BSS)
```

### tw nearest-pair \<sector\> [-n LIMIT]

Find nearest trade pairs to a sector (default limit 5).

```
  Nearest trade pairs to sector 865:

    1 hops - [246] (SSB) <-> [301] (BBS)  [3/3]
      buy Fuel Ore at [246], sell at [301]
      buy Organics at [246], sell at [301]
      buy Equipment at [301], sell at [246]
```

### tw sell [-n HOPS]

Find where to sell current cargo (default 10 hops). Uses player's current position and cargo from the database.

```
  Sell recommendations from sector 865:
    1 hops - [246] Port Alpha buys: Fuel Ore, Equipment
    3 hops - [301] Port Beta buys: Fuel Ore
```

Requires player status in DB. Errors if no cargo or no status.

### tw chat

Show recent chat messages (last 30).

```
  [radio] Trader1: anyone at stardock?
  [fed] Admin: server reset at 10pm
```

## Error Handling

- Missing database: prints error to stderr, exits 1
- No data for query: prints informational message (not an error)
- No path found: prints "No path from X to Y"
