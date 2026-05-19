# Feature Design: Profile-Based Configuration

STATUS: complete

## Use Cases (from user — do not modify)
1. As a user, I don't want to track DB files or configuration details after they are setup. The system should remember them under a profile.
2. As a user, I should be able to set a default profile that loads if I don't specify a specific profile.
3. As a user, I should be able to edit the config file with normal Unix tools to adjust details of my configuration such as what DB file I'm using.
4. As a user, I need a way to create a new profile, either as an explicit command or a natural flag I can use to specify a profile with an auto-create argument.
5. When a profile is created, it should setup the config with a new DB reference. The DB should be created when the game starts as it does now if the DB path doesn't exist.
6. As a user of previous versions, this should seamlessly transition me from the current approach to the new approach by creating the config for me and mapping in the default profile to the default DB that already exists.
7. With this feature, I no longer need the --db argument.
8. We will need to document moving DB files into a profile for users that might be using the --db flag.

## Problem
The guidance computer currently requires users to manually specify `--db` paths when playing on multiple TW2002 servers. As future features add more per-server configuration (sync buckets, experimental feature flags), the number of CLI arguments to remember per server grows unmanageable. Players need a "set it and forget it" approach where each server's configuration is stored under a named profile.

## Success Criteria
- [ ] A named profile stores all per-server settings (DB path, future: sync config, feature flags) — user never re-specifies after setup ← UC#1
- [ ] A default profile is used automatically when no `--profile` is specified ← UC#2
- [ ] Config file is plain INI, editable with any text editor ← UC#3
- [ ] A CLI mechanism exists to create new profiles ← UC#4
- [ ] New profiles auto-generate a DB path; DB is created lazily on first use ← UC#5
- [ ] First run on an upgraded system auto-creates config with default profile pointing to existing DB ← UC#6
- [ ] `--db` argument is removed from both `tw` and `tw-hud` ← UC#7
- [ ] Migration guide documents how to transition from `--db` usage to profiles ← UC#8

## User-Facing Behavior

### Config File

Location: `~/.config/tw-guidance-computer/config.ini`

Format: INI with `[DEFAULT]` section for globals that cascade to all profile sections (standard `configparser` behavior). Profile sections are namespaced as `[profile:<name>]` to leave room for future non-profile config sections.

```
[DEFAULT]
default_profile = saintcon
experimental = false

[profile:default]
db = ~/.local/share/tw-guidance-computer/game.db

[profile:saintcon]
db = ~/.local/share/tw-guidance-computer/saintcon.db
experimental = true

[profile:practice]
db = ~/.local/share/tw-guidance-computer/practice.db
```

A special key `default_profile` in `[DEFAULT]` specifies which profile to use when none is given. If `default_profile` is not set, the profile named `default` is used.

### Profile Selection

Both `tw` and `tw-hud` accept `--profile <name>` (short: `-p`):

```
tw-hud -p saintcon ~/tradewars/sessions/saintcon.log
tw -p saintcon sell
tw sell                    # uses default_profile from config
```

If `--profile` is not specified, the value of `default_profile` in `[DEFAULT]` is used. If `default_profile` is not set, the profile named `default` is used.

### Profile Creation

Two mechanisms — explicit management command and inline creation:

**Explicit command:**
```
tw profile create <name>
```

Creates a new profile section in the config file with an auto-generated DB path:

```
[profile:newserver]
db = ~/.local/share/tw-guidance-computer/newserver.db
```

If the profile already exists, the command errors: `Error: Profile 'newserver' already exists.`

**Inline creation on `tw-hud`:**
```
$ tw-hud -p newserver ~/sessions/newserver.log
Error: Profile 'newserver' not found. Hint: add --create to create it.

$ tw-hud -p newserver --create ~/sessions/newserver.log
Note: Created profile 'newserver' (db: ~/.local/share/tw-guidance-computer/newserver.db)
[HUD launches]
```

The `--create` flag is only available on `tw-hud` — it's the natural moment to create a profile (you're about to play on a new server). On `tw`, use `tw profile create` instead.

**In both cases:** the DB file is NOT created immediately — it's created lazily when the profile is first used (same as current behavior where the DB is created if the path doesn't exist).

### Profile Listing

```
tw profile list
```

Lists all configured profiles, marking the default:

```
  * saintcon (default)
    practice
    default
```

### Auto-Migration on First Run

When `tw` or `tw-hud` starts and no config file exists at `~/.config/tw-guidance-computer/config.ini`:

1. Create the config directory if needed
2. Create `config.ini` with:
   ```
   [DEFAULT]
   default_profile = default

   [profile:default]
   db = ~/.local/share/tw-guidance-computer/game.db
   ```
3. If the DB already exists at the default path, the user's data is preserved — the config just points to it.
4. Print a one-time notice to stderr: `Note: Created configuration at ~/.config/tw-guidance-computer/config.ini`

This means existing users upgrading see no behavior change — their existing DB is picked up automatically.

### Removed: --db Flag

The `--db` flag is removed from both `tw` and `tw-hud`. Users who were using `--db` to point at non-default databases should create a profile for each. The migration guide covers this.

### Error Handling

- Profile not found: `Error: Profile 'foo' not found. Run 'tw profile list' to see available profiles.`
- Config file malformed: `Error: Failed to parse config at ~/.config/tw-guidance-computer/config.ini: <details>`
- DB path in profile is not writable: existing behavior (SQLite error on open)

## Data Requirements

### Already Available
- Default DB path convention (`~/.local/share/tw-guidance-computer/game.db`)
- All current CLI argument parsing (argparse in `cli.py` and `hud.py`)

### New Data Needed
- None from the game session. This feature is purely infrastructure — no parser changes.

### Storage
- Config file: `~/.config/tw-guidance-computer/config.ini` (INI format, managed by `configparser`)
- No new database tables. The config lives outside the DB.

## Dependencies
- None. This is foundational infrastructure that future features (sync, experimental flags) will build on.

## Out of Scope
- Sync bucket configuration (future feature will add fields to profiles)
- Experimental feature flag implementation (future feature — this just reserves the field pattern)
- Per-profile log file paths (the log file is session-specific, passed as a positional arg to `tw-hud`)
- GUI or TUI config editor — the file is edited with Unix tools
- Config file encryption or secret management

## Open Questions
None — all resolved during discussion.

## TW Expert Notes
No game mechanic implications. This is pure infrastructure.
