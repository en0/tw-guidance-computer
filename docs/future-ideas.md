# Future Ideas

## Threat Tracker
- Track player sightings (warps in/out, lifts off, etc.) with sector and timestamp
- Maintain a hostiles list (manually entered enemies, players who have attacked us)
- Alert in the HUD when a known hostile is in or near your sector
- "Last seen" display: enemy name, sector, how many turns ago
- Correlate sector activity with known hostiles to identify scouting patterns

## Sector Activity Log
- Capture "player warps into/out of sector" events
- Capture "player lifts off from planet" events
- Display recent activity in the COMMS section or a dedicated section
- Useful for reviewing who was near you after the fact (scrolled off game terminal)

## Cost Basis Tracking (Refinement)
- Parse haggling sequences to determine actual purchase price per unit
- Show margin when a port offers to buy: "Org offered 35/u, cost 31.5/u, margin +11%"
- Track profit/loss per trade run

## Chat Parser
- Needs real message samples to match actual TW2002 format
- Sub-space radio, fed comm-link, hailing frequencies
- Corporate mail

## Dead-End Finder
- Identify sectors with only one warp in (good for hiding planets)
- Flag sectors behind chokepoints

## Graph Visualization
- Export sector graph to DOT format or similar
- Visual map of known space with port types annotated

## Watch Mode
- Auto-re-parse on file change without restarting the HUD
- Efficient incremental parsing (track byte offset, only parse new data)

## Shared Sector Intelligence
- Share sector topology (ports, planets, stardocks, warp connections) between allied players
- Mechanism: CSV reports pushed to a shared bucket (S3-compatible, specifics TBD)
- Each player's system periodically checks for new reports and imports them
- Ad-hoc CLI commands for manual push/pull (`tw intel push`, `tw intel pull` or similar)
- Source identifier: each row in the DB tracks who discovered it; only export YOUR discoveries (prevents infinite data inflation when re-sharing)
- Conflict resolution: server timestamp on port commodity data, freshest wins, local data breaks ties
- Trust model: corp allies only (shared bucket credentials)
- Granularity: full snapshot per push (revisit if performance becomes an issue)
- Player identity: parsed from session log; feature gated if identity not yet captured
- Scope: topology only — NOT player state (ship, cargo, credits, turns)
- Gate behind experimental feature flag (see "Experimental Feature Gates" below)

## Experimental Feature Gates
- CLI flag at startup to opt in to experimental features (e.g., `--experimental` or `--enable <feature>`)
- Allows testing incomplete or risky features without affecting stable workflow
- First candidate: Shared Sector Intelligence

## Low-Turn Safe Harbor Advisor
- When player runs low on turns, HUD lists nearby friendly planets and Federation space with shortest hops
- Helps the player find a safe place to park before logging off
- Needs: turn threshold detection, planet ownership/friendliness data, Federation sector identification, BFS from current position

## Multi-Server Configuration
- Config file supporting multiple TW2002 servers (different hosts, different databases)
- Each server gets its own database, player identity, and potentially different sharing groups
- Separate from shared intelligence but related (sharing is per-server)
- Needs independent scoping — captured here for future design work
