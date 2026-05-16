# Feature Design: Sector Art

STATUS: complete

## Use Cases (from user — do not modify)
1. When I travel to a sector with a port (e.g., sector 123 with "Regel Station"), I see a deterministically-generated ASCII art picture of that port on the HUD. The picture is generated from a hash of the port name, so my picture for Regel Station looks just like my buddy's Regel Station.
2. When I navigate to an empty sector, I see a starfield with nothing there.
3. When I arrive at a sector with a planet, it shows a planet as a 1/4 circle on the bottom left.
4. When I arrive at a sector with a stardock, it shows a picture of the stardock on the right, slightly up, looking far away.
5. When I arrive at a sector with more than one thing, it shows them all composed together: planet bottom-left, port in the middle (may slightly overlap planet if space is tight), stardock on the right slightly up.
6. Planet art can be a single reused picture (no variation needed).
7. Stardock art is a static picture (no variation needed).
8. From the CLI, I can view the sector art for any sector I've already visited — lets me recall what a place looked like without traveling back.

## Problem
The HUD has unused screen real estate. The player navigates between sectors constantly but gets no visual sense of "place." A sector with a famous port looks the same as an empty void. Adding deterministic ASCII art gives each sector a visual identity — ports feel like distinct locations, and the composition of elements (port, planet, stardock, starfield) communicates sector contents at a glance without reading text.

## Success Criteria
- [ ] Port art is deterministically generated from the port name hash — same name always produces the same art, across all players ← UC#1
- [ ] Empty sectors display a starfield (stars scattered in the art area) ← UC#2
- [ ] Sectors with a planet show a quarter-circle planet graphic anchored to the bottom-left of the art area ← UC#3
- [ ] Sectors with a stardock show a static stardock graphic positioned right-of-center, slightly elevated ← UC#4
- [ ] Multiple elements compose correctly: planet bottom-left, port center, stardock right — layered without destroying readability ← UC#5
- [ ] Planet art is a single static design, reused everywhere ← UC#6
- [ ] Stardock art is a single static design ← UC#7
- [ ] CLI command allows viewing sector art for previously visited sectors ← UC#8
- [ ] Art updates when the player moves to a new sector (triggered by sector change detection)

## User-Facing Behavior
A new panel in the HUD displays ASCII art representing the current sector's contents. The art area renders:

- **Starfield background**: Always present. Random-looking star characters (·, *, ., +) scattered across the art area, density ~1-3 per square inch of terminal space. For empty sectors, this is all you see.
- **Planet** (if present): A quarter-circle arc in the bottom-left corner. Static design with textured fill (varied characters suggesting terrain — blues, greens, browns with color). Bright limb on the curved edge (atmosphere glow). Drawn on top of the starfield.
- **Port** (if present): A deterministically-generated structure in the center of the art area. Generated using the WFC algorithm described below. Drawn on top of starfield and may slightly overlap planet.
- **Stardock** (if present): A static design positioned in the right portion of the art area, slightly above center. Smaller than the port art (conveys distance). Drawn on top of starfield.

The art refreshes whenever the player's current sector changes (detected via the existing sector parsing).

### CLI Command: `tw sector-art <sector_id>`

Renders the sector art for a previously visited sector to stdout with color. Looks up the sector's contents (port, planet, stardock) from the database and composes the scene. Errors if the sector hasn't been visited yet — discovery matters.

### Port Art Generation Algorithm (WFC-like Tile Placement)

The port art is generated using a Wave Function Collapse-inspired algorithm with run-length decay weighting. Reference implementation: `tools/station_gen.py`.

**Tile System:**
- A tile pack defines characters grouped by category: hull plating (`█ ▓ ░`), structural frame (`╔ ╗ ═ ║`), pipes (`─ │ ┌ ┐`), windows (`▪ ▫ [ ]`), antenna (`╥ ↑ ¤`), docking (`> < ⊏ ⊐`)
- Each tile has adjacency rules: which tile categories can appear north/south/east/west of it
- Hull and frame are dominant (~70% of interior); pipes, windows, antenna, docking are rare accents

**Generation Process:**
1. SHA-256 hash of port name → seed for deterministic RNG
2. Seed determines: silhouette shape, color scheme, density (0.3–1.0), symmetry (70% bilateral)
3. Silhouette mask defines the station's outer boundary (tower, dome, spire, wide, cross, diamond)
4. Grid collapses cell-by-cell (top-to-bottom, left-to-right), choosing tiles based on:
   - Adjacency constraints from already-placed neighbors
   - **Momentum**: tiles strongly prefer continuing the same category as neighbors (creates coherent zones)
   - **Run-length decay**: after a run exceeds ~2 cells, probability of continuation drops (prevents monotone blocks)
   - Density weighting controls empty vs filled ratio
5. Hard edge outline applied: border cells forced to frame characters (`╔ ╗ ╚ ╝ │ ─ / \`)
6. If symmetric: left half generated, then mirrored (with character flipping)

**Color System:**
- Seed selects a base hue family (steel, dark blue, warm gray, dark green, purple, rust, teal, charcoal)
- Base hue has 3-5 shade variations for hull/frame (dominant color)
- Each accent category gets complementary colors: pipes get one accent, windows another, antenna another
- Seed rotation varies which specific accents map to which categories
- Result: each station has a distinct color identity with complementary variation per subsystem

## Data Requirements

### Already Available
- Current sector ID (from player status)
- Port name and presence (from `get_port(sector_id)`)

### New Data Needed
- **Planet presence per sector**: The parser does not currently detect planets. The sector display in TW2002 shows planets as:
  ```
  Planets : <name> (<class>)
  ```
  This needs a new parser pattern and storage.
- **Stardock presence**: StarDock is detected via port class 0 ("Special"). This data is ALREADY available — `get_port(sector_id)` returns port_class. No new parser work needed for stardock.

### Storage
- Planets: needs a new table or column. Simplest: `planets` table with `sector_id` (boolean presence is sufficient, but storing name/class is cheap and future-proof).
- Stardock: No new storage needed — already detectable from existing port data (port_class == 0).

## Dependencies
- Existing sector change detection (parser already tracks current sector)
- Existing port data in the store
- New parser patterns for planets and stardock (Phase 2b work)
- HUD layout changes (need to allocate space for the art panel)

## Out of Scope
- Animated art or transitions between sectors
- Art for other sector entities (fighters, mines, beacons, etc.)
- User-configurable art styles or themes
- Unique planet art per planet (explicitly stated: single reused picture is fine)

## Resolved Questions
1. **HUD layout**: Art panel goes full-width in the bottom portion of the HUD, below the two-column content area. Fixed-content sections (Cargo, Sell Nearby, Trade Pairs) keep their exact positions and sizes. COMMS adapts to reduced available space (it already handles variable height). The art panel takes the remaining rows between the two-column area and the footer.
2. **Art panel dimensions**: Full terminal width, height = remaining rows below the two-column content area down to the footer. On a 30-row terminal this is roughly 12-15 rows × ~100 columns. On small terminals (< 25 rows), the art panel may be hidden entirely (graceful degradation).
3. **Planet detection**: Boolean only — "has planet" is sufficient. No need to parse planet names or classes.
4. **Stardock location**: NOT hardcoded to any sector. StarDock can be in any sector (user's server has it at sector 100). Detect via port class 0 ("Special") which indicates StarDock. StarDock always co-exists with a port.
5. **Starfield determinism**: Random on each sector arrival. The art (including starfield) is generated once when the player warps to a new sector and remains stable until the next sector change. The 250ms HUD refresh redraws the same cached art — no flicker.

## TW Expert Notes
- StarDock is a Class 0 / "Special" port. It is NOT fixed to sector 1 — varies by server configuration.
- StarDock always co-exists with a port (it IS a port, class 0).
- Planet display format in sector output: `Planets : <name> (<class>)` — needs parser pattern work.
- For this feature, planet detection only needs boolean presence (parser can capture more later if needed).
