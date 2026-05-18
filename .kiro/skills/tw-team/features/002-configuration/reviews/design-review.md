# Design Review — PM Adversary

## Verdict: PASS (with notes)

## Use Case Fidelity

All 8 user use cases are present verbatim in the "Use Cases" section. None dropped, merged, or reinterpreted. ✓

## Use Case Coverage

| UC | Requirement | Design Coverage | Status |
|----|-------------|----------------|--------|
| 1 | System remembers DB/config under a profile after setup | Named profile stores DB path + future settings; `--profile` selects; user never re-specifies | ✓ |
| 2 | Default profile loads if no specific profile specified | `default_profile` key in `[DEFAULT]`, fallback to profile named `default` | ✓ |
| 3 | Edit config with normal Unix tools | Plain INI format, `~/.config/` location, explicitly stated editable with any text editor | ✓ |
| 4 | Create new profile via explicit command or natural flag with auto-create | `tw profile create <name>` + `tw-hud --create` flag | ✓ |
| 5 | Profile creation sets up DB reference; DB created lazily | Auto-generated DB path on profile create; DB created lazily on first use | ✓ |
| 6 | Seamless transition from current approach | Auto-migration on first run creates config pointing to existing default DB | ✓ |
| 7 | No longer need --db argument | `--db` removed from both `tw` and `tw-hud` | ✓ |
| 8 | Document moving DB files into a profile | Migration guide mentioned in success criteria and "Removed: --db Flag" section | ✓ |

## Issues Found

### Issue 1: UC#4 says "either as an explicit command OR a natural flag" — design provides BOTH but restricts `--create` to `tw-hud` only (LOW)

The user said "a natural flag I can use to specify a profile with an auto-create argument." The design restricts `--create` to `tw-hud` only, with the rationale that it's "the natural moment." This is a reasonable design decision, but it's worth noting that the user didn't specify this restriction. If a user runs `tw -p newserver sell` and the profile doesn't exist, they get an error telling them to use `tw profile create` — they can't just add `--create` inline.

The UC says "either...or" — the user is satisfied with one mechanism. The design provides two. This is additive, not reductive. The restriction of `--create` to `tw-hud` is a UX judgment call, not a violation.

**Impact**: None. UC is satisfied — the user has both mechanisms available.

### Issue 2: `tw profile list` is not in any use case (INFORMATIONAL)

The design adds `tw profile list` which is not traced to any UC. This is reasonable supporting functionality (how else would you know what profiles exist?) but it's scope that wasn't explicitly requested.

**Impact**: Negligible. It's a trivial command that naturally supports the profile workflow. Not scope creep — it's implied by having profiles at all.

### Issue 3: STATUS typo — "iideation" (TRIVIAL)

Line 3: `STATUS: iideation` should be `STATUS: ideation`.

**Impact**: None. Cosmetic.

### Issue 4: UC#8 success criterion says "Migration guide documents..." but no deliverable location is specified (LOW)

The success criterion says a migration guide exists, but the design doesn't specify where it lives (README? docs/ directory? man page?). The builder will need to decide.

**Impact**: Low. The intent is clear — documentation must exist. Location is an implementation detail.

### Issue 5: `[DEFAULT]` section dual-purpose could confuse users editing the file (INFORMATIONAL)

Python's `configparser` treats `[DEFAULT]` specially — all keys in it cascade to every section. The design uses `[DEFAULT]` for both the `default_profile` meta-key AND for fallback values like `experimental = false`. A user editing the file might not understand that adding a key to `[DEFAULT]` affects all profiles. This is standard `configparser` behavior but could be surprising.

The design explicitly states "standard `configparser` behavior" and "Individual profiles override as needed" — so this is documented. Just noting it as a potential UX friction point for UC#3 (editing with Unix tools).

**Impact**: Informational. The design is correct; this is inherent to the INI format choice.

## Success Criteria Testability

| Criterion | Testable? | How |
|-----------|-----------|-----|
| Named profile stores settings | ✓ | Create profile, verify config file contains section with DB path |
| Default profile auto-selected | ✓ | Run `tw` without `--profile`, verify it uses default_profile value |
| Config is plain INI | ✓ | Read file with any INI parser, verify structure |
| CLI mechanism to create profiles | ✓ | Run `tw profile create foo`, verify section added |
| DB created lazily | ✓ | Create profile, verify no DB file; run command, verify DB created |
| Auto-migration on upgrade | ✓ | Delete config, run `tw`, verify config created pointing to existing DB |
| `--db` removed | ✓ | Run `tw --db foo`, verify argument rejected |
| Migration guide exists | ✓ | Check documentation file exists with relevant content |

All criteria are measurable and testable. ✓

## Data Availability

This feature requires no game session data. All data is infrastructure:
- Config file (created/managed by the application)
- Existing DB path convention (hardcoded)
- CLI argument parsing (existing argparse)

No parser changes needed. ✓

## Scope Check

No scope creep detected. The design explicitly defers:
- Sync bucket configuration
- Experimental feature flag implementation
- Per-profile log paths
- Config encryption

The `tw profile list` command is the only addition not directly traced to a UC, and it's a natural consequence of having profiles.

## Summary

The design is complete, faithful to all 8 use cases, and well-scoped. Success criteria are testable. No game data dependencies. The only actionable item is the STATUS typo.
