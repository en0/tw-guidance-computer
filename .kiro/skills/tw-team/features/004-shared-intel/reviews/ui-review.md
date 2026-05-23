# Adversarial Review: Feature 004 UI Spec

**Reviewer**: UI/UX (Adversary Mode)
**Date**: 2026-05-22
**Verdict**: FAIL — 3 issues require revision, 4 observations noted

---

## Critical Issues

### Issue 1: Header bar overflow on narrow terminals

**Problem**: The spec appends `  │  ! Intel E##` (13 chars) to the existing status bar. The current header renders sequentially: `Sector: NNN` + `  │  ` + `Turns: N,NNN` + `  │  ` + `Credits: N,NNN`. With a 4-digit sector, 4-digit turns, and 6-digit credits, the existing bar is already ~60 characters. Adding the intel indicator pushes to ~73 characters.

The HUD's minimum usable width is documented as "~100 columns" but there's no explicit size check — `_safe_addstr` silently truncates at screen edge. On a 80-column terminal (common for game sessions), the intel indicator will be truncated or invisible.

**Fix required**: Spec must define behavior when the indicator doesn't fit. Options:
- (a) Truncate credits display to make room (bad — hides useful data)
- (b) Only show `! E##` (7 chars shorter) when terminal is narrow
- (c) Define a minimum terminal width for the indicator to appear (e.g., 90+ cols)

### Issue 2: `A_BLINK` is unreliable and potentially invisible

**Problem**: The spec uses `curses.A_BLINK` for the error indicator. Terminal support for `A_BLINK` is inconsistent:
- `st-256color` (the player's terminal per session capture docs): blink support depends on build flags
- Many modern terminals ignore `A_BLINK` entirely (iTerm2, some xterm configs)
- If blink doesn't work, the indicator is just static red text — which may not be noticed since the player is focused on the game terminal, not the HUD

The RED ALERT overlay from Feature 003 does NOT use `A_BLINK` — it uses red bold with high contrast (white on red background). The intel indicator relies solely on blink for attention, which is a weaker and less portable signal.

**Fix required**: Use `A_REVERSE` (red background, guaranteed visible) as the primary attention mechanism. `A_BLINK` can be added as a bonus but must not be the only differentiator from normal text.

### Issue 3: Shutdown modal dimensions inconsistent with mockup

**Problem**: The spec states "Dimensions: 35×5 characters (fixed width)" but the mockup shows:

```
╔════════ Syncing Intel ════════╗
```

Counting characters in the mockup: that's 33 characters wide. The failure state content:

```
║   Push failed: server unreachable ║
```

That's 37 characters (3 padding + 31 message + 3 padding). The "fixed width" of 35 cannot accommodate the longest failure message shown in the spec.

**Fix required**: Either:
- (a) Define the actual width needed (measure longest content + padding + borders) — likely 39-41 chars
- (b) Truncate failure reasons to fit 35 chars (and document the truncation)
- (c) Make width dynamic based on content (like the RED ALERT overlay which is "approximately 50×10")

---

## Observations (non-blocking)

### Observation 1: Design doc shows full keyhash in CLI, spec truncates to 8 chars

The design doc's CLI example shows: `Downloading a3f2b8c9d1e4f567890abcdef1234567890abcdef1234567890abcdef12345678... (45KB)`

The UI spec shows: `Downloading a3f2b8c9... (45KB)`

The spec's truncation to 8 chars is better for readability, but this is a deviation from the design doc. The spec should explicitly note this as a UI decision (truncated for display) so the builder doesn't implement the full hash.

**Severity**: Low — the spec's choice is correct, just needs to be explicit about the deviation.

### Observation 2: No interaction between RED ALERT overlay and shutdown modal

If the player is in RED ALERT state (turns < 50) and presses `q`, both the RED ALERT overlay and the shutdown modal would want to render. The spec doesn't address z-order or which takes priority.

**Recommendation**: Shutdown modal should replace/suppress the RED ALERT overlay (shutdown is the active state, alert is informational). Document this explicitly.

### Observation 3: "Done." display timing is fragile

The spec says: "After 'Done.' displays for 500ms, then HUD exits." This relies on the 250ms render loop catching the "Done." state and then waiting an additional 500ms. If the render loop is at the wrong phase, the player might see "Done." for anywhere between 250ms and 750ms, or potentially miss it entirely if the exit races the render.

**Recommendation**: Use a dedicated timer (not render-loop-dependent) for the done/failure display duration, or accept that the timing is approximate and document it as "at least 500ms."

### Observation 4: CLI progress output assumes terminal (not piped)

The spec shows progress lines printing as each phase completes. If stdout is piped (e.g., `tw intel push > log.txt`), the line-by-line progress is fine. But if stderr is piped separately, the error output goes to stderr while progress goes to stdout — this is correct behavior but worth noting for the builder.

No action needed — the spec's stdout/stderr split is correct.

---

## Consistency Check

| Aspect | Existing Pattern | Spec | Match? |
|--------|-----------------|------|--------|
| Overlay box chars | `╔═╗║╚═╝` (Feature 003) | `╔═╗║╚═╝` | ✓ |
| Overlay centering | `(max_y - h) // 2`, `(max_x - w) // 2` | Same formula | ✓ |
| Color pair usage | 1=green, 2=cyan, 3=yellow, 4=red, 5=magenta | Uses pairs 1,2,4 | ✓ |
| No new color pairs | 5 existing pairs | No new pairs added | ✓ |
| Overlay color | Feature 003: red border (pair 4) | Feature 004: cyan border (pair 2) | ✓ (appropriate — info vs. alarm) |
| Header separator style | `  │  ` (2 spaces each side) | Same | ✓ |
| Signal handling | Feature 003: no special handling | Feature 004: defines full signal table | ✓ (new behavior) |

---

## Verdict: FAIL

Three issues must be addressed before this spec can move to implementation:

1. **Header overflow** — define behavior for narrow terminals
2. **A_BLINK reliability** — use A_REVERSE as primary attention mechanism
3. **Modal width** — reconcile stated dimensions with actual content width

The observations are informational and can be addressed during implementation planning, but the three critical issues affect whether the spec is implementable as written.
