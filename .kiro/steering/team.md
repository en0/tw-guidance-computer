---
inclusion: always
---
# Development Team

This project uses an AI development team with adversarial validation loops.

## Agents

| Agent | Role | Focus |
|-------|------|-------|
| **Team Lead** | Orchestrator | Single point of contact, drives pipeline, assigns work to specialists |
| PM | Product Manager | Refines ideas, produces feature design docs, validates deliverables |
| TW Expert | Trade Wars 2002 Specialist | Game mechanics authority, researches TW2002, validates game logic |
| Architect | Software Architect | Designs implementation plans, validates against codespecs, identifies parallel work |
| UI/UX | Interface Designer | Designs TUI/HUD interactions, produces interface specs |
| Parser Expert | Log Parser Specialist | Deep knowledge of ANSI data stream, builds pattern knowledge base |
| Builder | Implementer | Writes code + tests, follows architect's plan |

## Adversarial Loop Protocol

Every agent operates in two modes:

1. **Creator mode** — Produces the deliverable (design doc, spec, code, etc.)
2. **Adversary mode** — Fresh instance scrutinizes the output with a critical lens

The adversary is the *same role* with a mandate to find flaws — not a different role reviewing. This catches self-consistency issues, spec violations, and blind spots that the creator missed.

## Feature Artifacts

All artifacts for a feature live together in `.kiro/skills/tw-team/features/NNN-slug/`:

```
features/001-threat-tracker/
├── design.md          # PM output
├── impl-plan.md       # Architect output
├── ui-spec.md         # UI/UX output
└── reviews/           # Adversarial review notes
```

See `features/README.md` for lifecycle and conventions.

- `parser-patterns/` — ANSI escape sequences, game output formats, regex patterns that work
- `tw-mechanics/` — Game rules, trading formulas, sector behavior, player interactions
- `decisions/` — Architecture decisions, rejected approaches, why things are the way they are

## Shared Knowledge Base

Located at `.kiro/skills/tw-team/knowledge/`. Agents write discoveries here so knowledge persists across sessions:

- `parser-patterns/` — ANSI escape sequences, game output formats, regex patterns that work
- `tw-mechanics/` — Game rules, trading formulas, sector behavior, player interactions
- `decisions/` — Architecture decisions, rejected approaches, why things are the way they are

## Session Data

Raw game session logs live at `~/traidwars/sessions/`. These are `script -f` captures of SSH sessions to TW2002 with heavy ANSI escape codes. The parser expert uses these to discover and document patterns.

## Project Architecture

This project follows hexagonal architecture. See `docs/codespecs/` for the full specification set.
