---
name: TW Team
description: AI development team knowledge base for the TW Guidance Computer. Contains parser patterns, game mechanics, architecture decisions, and document templates. Activated when any team agent is working on this project.
---

# TW Team Knowledge Base

Shared knowledge that persists across agent sessions.

## Structure

- `knowledge/product/` — Current product state: HUD layout, CLI commands, data flow, capabilities
- `knowledge/parser-patterns/` — Discovered patterns in the TW2002 data stream
- `knowledge/tw-mechanics/` — Game rules, formulas, behaviors
- `knowledge/decisions/` — Architecture decisions and rejected approaches
- `templates/` — Document templates for feature designs, impl plans, UI specs
- `features/` — Feature artifacts organized by number (`NNN-slug/` per feature)

## Usage

Any agent that discovers something writes it to the appropriate knowledge file. Files are markdown. One topic per file. Use descriptive filenames.

### Parser Patterns Format

```markdown
# [Pattern Name]

## What It Captures
Brief description.

## Raw Example (with ANSI noted)
The actual bytes from a session log.

## Clean Text (after strip)
What the parser sees.

## Regex
The pattern that matches.

## Edge Cases
Known variations or gotchas.
```

### Game Mechanics Format

```markdown
# [Mechanic Name]

## How It Works
Description of the game behavior.

## What the Player Sees
Terminal output during this mechanic.

## Relevant to Parser?
Whether this produces parseable output and what data can be extracted.

## Sources
How this was verified (session logs, documentation, testing).
```
