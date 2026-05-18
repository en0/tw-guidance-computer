# Validation: PM — Code vs Feature Design & Use Cases

## Verdict: PASS (with one gap)

## Use Case Verification

| UC | Requirement | Implementation | Status |
|----|-------------|---------------|--------|
| 1 | System remembers settings under a profile — user never re-specifies after setup | `IniProfileStore` persists profile with `db_path` in INI config. `resolve_db_path()` reads it automatically. User only specifies `--profile` once or uses default. | ✓ |
| 2 | Default profile loads if no specific profile specified | `resolve_db_path(None)` calls `store.list_profiles().default_name` which reads `default_profile` from `[DEFAULT]` section. Falls back to `"default"`. | ✓ |
| 3 | Config file is plain INI, editable with Unix tools | `IniProfileStore` uses `configparser`. File at `~/.config/tw-guidance-computer/config.ini`. Standard INI format with `[profile:name]` sections. | ✓ |
| 4 | Way to create a new profile (explicit command OR natural flag with auto-create) | `tw profile create <name>` in `cli.py`. `tw-hud -p <name> --create` in `hud.py`. Both paths call `CreateProfile.execute()`. | ✓ |
| 5 | Profile creation sets up DB reference; DB created lazily | `CreateProfile.execute()` calls `resolve_default_db_path(name)` to generate path, saves to config. `AppContext.__init__` calls `db_path.parent.mkdir(parents=True, exist_ok=True)` but SQLite creates the DB file on first connection — lazy. | ✓ |
| 6 | Seamless transition from current approach (auto-migration) | `resolve_db_path()` calls `store.ensure_config_exists()` which creates config with `[profile:default] db = ~/.local/share/tw-guidance-computer/game.db` if no config exists. Existing DB at that path is preserved — the config just points to it. | ✓ |
| 7 | No longer need --db argument | `--db` flag is completely absent from both `cli.py` and `hud.py`. Grep confirms no `"--db"` or `'--db'` anywhere in the Python source. | ✓ |
| 8 | Documentation for migrating from --db | **NOT FOUND.** No migration guide exists in `docs/`, `README.md`, or anywhere in the repository. | ⚠️ |

## Detailed Findings

### UC#1 — Profile Remembers Settings ✓

The `Profile` domain model stores `name` and `db_path`. The `IniProfileStore` persists this to disk as an INI section. Once a profile is created, the user runs `tw -p saintcon sell` or sets `default_profile = saintcon` in the config and just runs `tw sell`. No re-specification needed.

### UC#2 — Default Profile ✓

`resolve_db_path(None)` → `store.list_profiles().default_name` → reads `default_profile` from `[DEFAULT]` section. If not set, `ensure_config_exists()` always writes `default_profile = default`. The `ProfileListing` validates `default_name` is non-empty.

### UC#3 — Plain INI ✓

Config format is standard `configparser` INI:
```ini
[DEFAULT]
default_profile = default

[profile:default]
db = ~/.local/share/tw-guidance-computer/game.db
```

Editable with `vim`, `nano`, `sed`, etc. File permissions set to `0o600` on creation.

### UC#4 — Profile Creation ✓

Two mechanisms implemented:

1. **Explicit**: `tw profile create saintcon` → prints `Created profile 'saintcon' (db: ~/.local/share/tw-guidance-computer/saintcon.db)`
2. **Inline**: `tw-hud -p saintcon --create ~/sessions/log` → creates profile if missing, prints note to stderr, continues to launch HUD

Edge case handled: `--create` with an already-existing profile silently continues (catches `ProfileExistsError`).

### UC#5 — DB Created Lazily ✓

`CreateProfile.execute()` generates the path string via `resolve_default_db_path(name)` and saves it to config. The DB file is NOT created at this point. When the profile is later used (`AppContext(db_path=...)`), `SqliteGameStateStore` opens the SQLite connection which creates the file if absent. The parent directory is created by `AppContext.__init__`.

### UC#6 — Seamless Transition ✓

`resolve_db_path()` calls `store.ensure_config_exists()` on every invocation. If no config file exists:
1. Creates `~/.config/tw-guidance-computer/config.ini`
2. Writes default profile pointing to `~/.local/share/tw-guidance-computer/game.db`
3. Existing DB at that path is preserved — the config just points to it

Users upgrading from the old `--db`-less default behavior see no change. Their existing DB is picked up automatically.

### UC#7 — --db Removed ✓

Confirmed via grep: no `"--db"` or `'--db'` string exists in any `.py` file. Both `cli.py` and `hud.py` use `--profile / -p` instead.

**Note**: The impl plan specified printing a helpful error if `--db` is detected (via argparse unknown args). This is NOT implemented — argparse will just show its standard "unrecognized arguments" error. This is acceptable (the error is still clear) but doesn't match the plan's specified behavior.

### UC#8 — Migration Documentation ⚠️

**Gap found.** The design specifies:
> "Migration guide documents how to transition from `--db` usage to profiles"

No migration guide exists anywhere in the repository:
- `README.md` doesn't mention profiles at all
- No `docs/migration.md` or similar file exists
- No `CHANGELOG` or `UPGRADING` document exists

The design's "Removed: --db Flag" section says: "Users who were using `--db` to point at non-default databases should create a profile for each. The migration guide covers this."

This documentation deliverable is missing.

## Success Criteria Check

- [x] Named profile stores per-server settings — user never re-specifies after setup ← UC#1
- [x] Default profile used automatically when no `--profile` specified ← UC#2
- [x] Config file is plain INI, editable with any text editor ← UC#3
- [x] CLI mechanism exists to create new profiles ← UC#4
- [x] New profiles auto-generate a DB path; DB created lazily on first use ← UC#5
- [x] First run on upgraded system auto-creates config with default profile pointing to existing DB ← UC#6
- [x] `--db` argument removed from both `tw` and `tw-hud` ← UC#7
- [ ] Migration guide documents how to transition from `--db` usage to profiles ← UC#8 **MISSING**

## Implementation Quality Notes

- Domain validation is thorough: name regex, length limit, hyphen rules
- Error handling is user-friendly: `ConfigError` and `ProfileNotFoundError` caught at entry points with actionable messages
- `ProfileExistsError` on `--create` is silently swallowed (correct — idempotent behavior)
- Config file created with `0o600` permissions (security-conscious)
- `~` expansion handled correctly in `get_profile()` via `os.path.expanduser()`
- "default" → "game.db" special case correctly in `resolve_default_db_path()`

## Action Required

**UC#8**: A migration guide needs to be written. Suggested content:
- Where the config file lives (`~/.config/tw-guidance-computer/config.ini`)
- How to create a profile for an existing DB: `tw profile create <name>` then edit config to point `db` at the existing file
- How to set a default profile (`default_profile` in `[DEFAULT]`)
- Note that `--db` no longer works and argparse will reject it

This is a documentation task, not a code task. The feature is functionally complete.
