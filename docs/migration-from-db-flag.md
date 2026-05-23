# Migrating from --db to Profiles

The `--db` flag has been removed from both `tw` and `tw-hud`. Configuration is now managed through named profiles stored in `~/.config/tw-guidance-computer/config.ini`.

## Automatic Migration

If you were using the default database path (`~/.local/share/tw-guidance-computer/game.db`), no action is needed. On first run, the system creates a config file with a `default` profile pointing to your existing database.

## If You Were Using --db

If you had scripts or aliases using `--db` to point at a custom database file, create a profile for each:

```bash
# Create a profile
tw profile create myserver

# Edit the config to point at your existing DB
vim ~/.config/tw-guidance-computer/config.ini
```

In the config file, update the `db` path for your new profile:

```ini
[profile:myserver]
db = /path/to/your/existing/database.db
```

Then use `--profile` (or `-p`) instead of `--db`:

```bash
# Before
tw --db /path/to/game.db sell
tw-hud --db /path/to/game.db ~/sessions/log

# After
tw -p myserver sell
tw-hud -p myserver ~/sessions/log
```

## Setting a Default Profile

To avoid typing `-p` every time, set your preferred profile as the default:

```ini
[DEFAULT]
default_profile = myserver
```

Then just run `tw sell` or `tw-hud ~/sessions/log` — it uses the default automatically.

## Auto-Creating Profiles on tw-hud

When starting a HUD session for a new server, use `--create` to make the profile in one step:

```bash
tw-hud -p newserver --create ~/sessions/newserver.log
```

This creates the profile with an auto-generated DB path and launches the HUD immediately.

## Config File Reference

Location: `~/.config/tw-guidance-computer/config.ini`

```ini
[DEFAULT]
default_profile = default

[profile:default]
db = ~/.local/share/tw-guidance-computer/game.db

[profile:myserver]
db = ~/.local/share/tw-guidance-computer/myserver.db
```

Profile names must be lowercase alphanumeric with hyphens (1–64 chars, no leading/trailing hyphens).

## Listing Profiles

```bash
tw profile list
```

Output marks the default with `*`:

```
  * myserver (default)
    practice
    default
```
