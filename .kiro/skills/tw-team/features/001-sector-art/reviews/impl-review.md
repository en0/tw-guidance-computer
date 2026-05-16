# Implementation Plan Review — Architect Adversary

## Verdict: PASS (with notes for builder)

## Architecture Compliance

### Dependency Rule
- Domain (Unit 1, Unit 5): imports only stdlib. No I/O, no framework deps. ✓
- Application (Unit 2, Unit 4, Unit 6): imports from domain and ports only. ✓
- Adapters (Unit 3, Unit 7, Unit 8): imports from application and domain. ✓

No dependency direction violations.

### Layer Placement
- Planet model → domain ✓
- Port extension → application/ports ✓
- Art generation → domain (pure functions, stdlib only) ✓
- RenderSectorArt → application (orchestration) ✓
- SQLite, TUI, CLI → adapters ✓

All code is in the correct layer.

## Issues Found

### Issue 1: Planet model lacks `__post_init__` validation (LOW)

Per Domain-Value-Objects codespec: "If a field has constraints, enforce them at construction." Planet class is constrained to a single uppercase letter (A-Z per observed data). The plan specifies `planet_class: str` with no validation. Should have:

```python
def __post_init__(self) -> None:
    if len(self.planet_class) != 1 or not self.planet_class.isupper():
        raise ValueError("planet_class must be a single uppercase letter")
    if self.sector_id < 1:
        raise ValueError("sector_id must be positive")
```

**Impact**: Low. Builder should add this. Won't affect other units.

### Issue 2: Unit 4 placement description is misleading (LOW)

The plan says planet regex is "Placed in `_extract_sectors_and_warps` after port detection." But looking at the actual parser, `_extract_sectors_and_warps` and `_extract_ports` are separate methods called sequentially from `execute()`. The planet line appears in the sector display block (after port line, before warp line), so it logically belongs in `_extract_sectors_and_warps` — but the phrase "after port detection" is confusing because port detection is a different method.

**Recommendation**: Either add planet extraction as a new private method `_extract_planets(text)` called from `execute()`, or clarify that it goes in `_extract_sectors_and_warps` after the sector ID regex match (since the planet line is part of the sector display block).

**Impact**: Low. Builder will see the actual code structure and place it correctly.

### Issue 3: Starfield seed source unspecified in use case (LOW)

`compose_scene()` takes a `seed: int` parameter for the starfield. The use case `RenderSectorArt.execute(sector_id, width, height)` doesn't expose a seed parameter. Where does the seed come from?

Options:
- Use case generates a random seed internally (CLI output varies per invocation — acceptable per design: "Random on each sector arrival")
- Use case derives seed from sector_id (starfield is deterministic per sector — contradicts design)
- HUD adapter passes a cached seed; CLI generates fresh each time

The design explicitly says starfield is "random on each sector arrival" and only PORT art must be deterministic. So the use case generating a random seed is correct behavior. The HUD adapter caches the entire rendered grid (not the seed), so the 250ms refresh redraws the same cached output.

**Impact**: Low. The correct answer is: use case uses `random.randint()` for the seed. Domain functions remain pure (they receive the seed). This is fine — `random` is stdlib, not I/O.

### Issue 4: Parallel execution group B has a sequencing error (LOW)

The plan says:
> B (after A): Unit 2, Unit 4. Unit 2 needs Unit 1. Unit 4 needs Unit 2.

If Unit 4 needs Unit 2, they can't be in the same parallel group. Unit 4 must come AFTER Unit 2. The table should show Unit 2 in group B and Unit 4 in group C (after B). The "Realistic execution" line says "A → B+C → D → E" which also doesn't capture that Unit 4 depends on Unit 2.

Looking more carefully: Unit 4 needs the `upsert_planet` method on the store (Unit 2 defines it). So Unit 4 must wait for Unit 2. The parallel plan should be:
- A: Unit 1, Unit 5 (parallel)
- B: Unit 2 (after Unit 1)
- C: Unit 3, Unit 4 (after Unit 2, parallel — different files)
- D: Unit 6 (after Unit 2, Unit 5)
- E: Unit 7, Unit 8 (after Unit 6, parallel)

**Impact**: Low. Affects scheduling only, not correctness. A single builder doing them sequentially won't hit this.

## Codespec Compliance

| Spec | Status |
|------|--------|
| Hexagonal Architecture | ✓ Layers correct, dependency direction correct |
| Use Case Pattern | ✓ @final, execute(), constructor injection |
| Port Definitions | ✓ Protocol extension, domain types |
| Domain Value Objects | ⚠ Missing validation (Issue 1) |
| Testing Strategy | ✓ Mirror structure, appropriate test types per layer |
| Typing Discipline | ✓ Plan implies @final on use case, @override on adapter methods |
| Minimal Dependencies | ✓ No new external deps, stdlib only for art |
| Composition Root | ✓ Not modified (use case wired in existing roots) |

## Risk Assessment

- **256-color curses**: Real risk, correctly identified. Raw ANSI in addstr is the standard workaround. Fallback to 8-color noted. ✓
- **Performance**: WFC on 25×12 grid is trivially fast. Caching eliminates refresh concern. ✓
- **File conflicts between parallel units**: None detected. ✓

## Summary

The plan is sound and follows the codespecs. The issues are all LOW severity — resolvable by the builder during implementation without requiring plan revision. The architecture is clean, the parallel groups are mostly correct (minor sequencing note), and no new external dependencies are introduced.
