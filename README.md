# tw-guidance-computer

Trade Wars 2002 guidance computer — real-time HUD and query tool that parses your game session log and builds a persistent knowledge base.

![Sector Art HUD](docs/images/sector-art.png)

## Usage

Two entry points:

- `tw-hud <logfile> [--parse-existing]` — runs the live HUD, tails the log, updates SQLite
- `tw <command>` — queries the SQLite DB

### Workflow

1. Start your game session: `script -f ~/src/tw/session2.log` then SSH in
2. In another terminal: `tw-hud ~/src/tw/session2.log --parse-existing`
3. In a third terminal: `tw pairs`, `tw path 865 246`, `tw sell`, etc.

### CLI Commands

```
tw status              # Database summary
tw sector <id>         # Show sector info
tw ports [-t TYPE]     # List known ports
tw pairs               # Find adjacent trade pairs
tw path <start> <end>  # Find shortest path
tw search <pattern>    # Search ports by type (* = wildcard)
tw nearby <sector> -n  # Find ports within N hops
tw sell                # Find where to sell current cargo
tw chat                # Show recent chat messages
```

### HUD Sections

- **Status bar** — current sector, turns remaining, credits
- **Cargo** — what you're carrying with cost basis, so you can evaluate sell offers against your investment
- **Sell nearby** — closest ports that buy what you're holding
- **Trade pairs** — best adjacent complementary port pairs
- **Comms** — sub-space radio and fed comm-link messages

## Architecture

Hexagonal architecture per [codespecs](docs/codespecs/).

```
src/tw_guidance_computer/
├── domain/
│   ├── models.py              # Sector, Port, CargoHold, PlayerStatus, TradePair
│   └── exceptions.py          # GuidanceError hierarchy
├── application/
│   ├── ports/
│   │   ├── game_state_store.py    # Protocol for persistence
│   │   └── log_reader.py         # Protocol for log input
│   ├── parse_log_chunk.py        # Core parser use case
│   ├── find_trade_pairs.py       # Adjacent complementary port finder
│   ├── find_path.py              # BFS pathfinding
│   └── find_sell_locations.py    # Nearest buyer for current cargo
├── adapters/
│   ├── sqlite_store.py        # SQLite implementation (WAL mode, concurrent-safe)
│   ├── log_reader.py          # tail -f style reader + ANSI stripper
│   └── tui.py                 # Curses HUD
├── hud.py                     # Composition root: tw-hud
└── cli.py                     # Composition root: tw
```

## Setup

```bash
# With uv (recommended)
uv sync

# With pip
pip install -e .
```

## Install from GitHub

```bash
# With uv
uv pip install git+https://github.com/en0/tw-guidance-computer.git

# With pip
pip install git+https://github.com/en0/tw-guidance-computer.git
```

## Development

```bash
uv run pytest           # run tests
uv run mypy src/        # type check
uv run ruff check src/  # lint
```

This project uses an AI development team for new features. See [`.kiro/README.md`](.kiro/README.md) for the workflow.

## Data

The SQLite database persists at `~/.local/share/tw-guidance-computer/game.db` and accumulates knowledge across sessions.
