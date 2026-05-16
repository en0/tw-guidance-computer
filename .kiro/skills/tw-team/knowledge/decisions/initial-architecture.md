# Initial Architecture Decisions

## Hexagonal Architecture
Adopted from the start. Domain types are frozen dataclasses. Use cases are @final with execute(). Ports are Protocols. Adapters handle all I/O.

**Why**: The parser is complex enough that separating concerns is essential. The domain types (Sector, Port, WarpConnection, etc.) are shared across multiple use cases and both interfaces (HUD + CLI).

## SQLite with WAL Mode
Single SQLite database at `~/.local/share/tw-guidance-computer/game.db`. WAL mode enables concurrent reads (CLI queries) while the HUD writes.

**Why**: The HUD writes continuously as it parses. The CLI reads on-demand. WAL mode handles this without locking conflicts.

## ANSI Stripping in Adapter, Parsing in Application
The log reader adapter strips ANSI escape codes. The parser use case receives clean text.

**Why**: ANSI stripping is an I/O concern (translating raw bytes to domain-usable text). The parser's regex patterns are complex enough without also handling escape sequences.

## Stateful Parser
`ParseLogChunk` maintains state across calls (current sector, turns, credits, cargo). It's constructed once and called repeatedly as new data arrives.

**Why**: Game state is cumulative. A sector display tells you where you are, but cargo state persists until a transaction changes it. The parser must track running state.

## Cost Basis Tracking
Cargo tracks cost_per_unit using weighted average when buying more of the same commodity.

**Why**: The player needs to know their break-even price when evaluating sell offers. Without cost basis, you can't calculate margin.
