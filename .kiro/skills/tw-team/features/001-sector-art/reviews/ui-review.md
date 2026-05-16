# UI Spec Review — UI/UX Adversary

## Verdict: PASS (with issues to resolve during build)

## Glanceability

The art panel is ambient — it communicates sector contents through visual pattern (port shape, planet arc, stardock silhouette) rather than requiring reading. This is appropriate for a secondary display the player glances at between game actions. The information hierarchy is correct: actionable data (cargo, pairs, sell advice) stays above the art panel. ✓

## Layout Concerns

### Issue 1: Two-column / art-panel height split is underspecified (MEDIUM)

The spec says the art panel gets "remaining rows below two-column area." But it doesn't define how many rows the two-column area gets. Currently, COMMS fills all available vertical space in the right column. With the art panel introduced, something has to give.

The design says "Fixed-content sections (Cargo, Sell Nearby, Trade Pairs) keep their exact positions and sizes. COMMS adapts to reduced available space."

**What's missing**: A concrete rule for the split point. Options:
- Two-column area has a fixed height (e.g., 12 rows), art gets the rest
- Two-column area grows to fit Cargo + Sell Nearby + Pairs, COMMS gets 3-5 rows max, art gets the rest
- Art panel has a fixed height, two-column area gets the rest

Without this, the builder will have to make a judgment call. Recommend: define a minimum art panel height (e.g., 6 rows) and a maximum two-column height, with COMMS as the flex element.

**Impact**: Medium. Builder can resolve this, but it should be a conscious design decision, not an implementation accident.

### Issue 2: Footer placement in mockup is clear (OK)

The mockup shows `[q] quit  [t] toggle pairs` at the bottom, below the art. This is consistent with the current HUD (footer at terminal bottom). The art panel sits between the two-column content and the footer. ✓

## Terminal Size Handling

- < 25 rows: panel hidden. ✓
- 25-29 rows: 6-10 rows for art. ✓
- ≥ 30 rows: 12-15 rows. ✓

Graceful degradation is well-defined. The existing layout is preserved when the terminal is too small. ✓

## Color Scheme

Colors are meaningful, not decorative:
- Starfield dim (doesn't compete) ✓
- Planet earth tones (natural, recognizable) ✓
- Port seed-based (identity — each station looks different) ✓
- Stardock neutral/distant (conveys far away) ✓

No conflict with the game's own ANSI colors or the existing HUD palette (green/cyan/yellow/red/magenta). The 256-color art panel is visually distinct from both. ✓

## States

All states covered:
- Full scene (port + planet + stardock) ✓
- Port only ✓
- Planet only (rare — sector with planet but no port) ✓
- Empty sector (starfield only) ✓
- Small terminal (hidden) ✓

No state produces confusing or broken output. ✓

## CLI Command

- `tw sector-art <sector_id>` — memorable, consistent with existing `tw sector <id>` pattern. ✓
- Fixed 80×14 canvas for CLI output — good, avoids terminal-width dependency. ✓
- Error message for unexplored sector is clear. ✓
- Header line `─── Sector 865: The Federation ───` provides context. ✓

## Interaction

- No interaction with art panel (purely informational). ✓
- Existing keybindings unchanged. ✓
- No cursor in art area. ✓
- Cached between sector changes (no flicker on 250ms refresh). ✓

## Would This Help During Gameplay?

It's not decision-support — it's spatial memory and atmosphere. A player who's been to 50 sectors will start recognizing stations by their visual shape/color. "The big blue one" vs "the small rust-colored one." The CLI recall command (`tw sector-art 865`) has clear utility for route planning — "what was at that sector again?"

Not every HUD element needs to be actionable. Ambient information that builds familiarity with the game world has value, especially for a game where sector knowledge is competitive advantage.

## Summary

The spec is implementable and well-thought-out. The one real gap is the height allocation between the two-column area and the art panel — this needs a concrete rule before build, or the builder needs explicit latitude to decide.
