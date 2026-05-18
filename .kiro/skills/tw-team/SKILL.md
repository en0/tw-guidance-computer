---
name: TW Team
description: AI development team knowledge base for the TW Guidance Computer. Contains parser patterns, game mechanics, architecture decisions, and document templates. Activated when any team agent is working on this project.
---

# TW Team Knowledge Base

Shared knowledge that persists across agent sessions.

## Structure

- `.kiro/skills/tw-team/knowledge/product/` — Current product state: HUD layout, CLI commands, data flow
- `.kiro/skills/tw-team/knowledge/parser-patterns/` — Discovered patterns in the TW2002 data stream
- `.kiro/skills/tw-team/knowledge/tw-mechanics/` — Game rules, formulas, behaviors
- `.kiro/skills/tw-team/knowledge/decisions/` — Architecture decisions and rejected approaches
- `.kiro/skills/tw-team/templates/` — Document templates (feature designs, impl plans, UI specs)
- `.kiro/skills/tw-team/features/` — Feature artifacts by number (`NNN-slug/`)

## Rules

- Any agent that discovers something writes it to the appropriate knowledge file
- One topic per file, descriptive filenames, markdown format
- Use templates in `.kiro/skills/tw-team/templates/` for feature artifacts — don't invent formats
