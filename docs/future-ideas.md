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

## Experimental Feature Gates
- CLI flag at startup to opt in to experimental features (e.g., `--experimental` or `--enable <feature>`)
- Allows testing incomplete or risky features without affecting stable workflow

## CLI Config Command
- `tw [--profile=PROFILE] config` — view/modify profile values from the CLI without editing the INI directly
- Set values: `tw config set intel_host intel.example.com`
- View values: `tw config show` (dump current profile's config)
- Removes the need for users to know the INI file location or format
- Respects `--profile` flag to target a specific profile

## Multi-Instance HUD Detection
- On startup, check if another HUD process is already running for the same profile
- If detected: disable all sync (intel AND log file tailing), operate in read-only mode pulling from DB only
- Display a status indicator on the HUD showing "offline" or "read-only" state
- Prevents concurrent write conflicts on the SQLite DB and double-syncing intel
- Detection mechanism TBD (PID file, flock, etc.)

## End-User Documentation
- Proper docs site or structured documentation beyond README
- Installation guide, configuration reference, feature walkthroughs
- Intel server setup guide (dedicated page with hardening tips, key management, troubleshooting)
- Profile management guide (creating, switching, editing config)
- HUD usage guide (keybindings, sections explained, what each display means)
