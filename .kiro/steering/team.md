---
inclusion: always
---
# Development Team

AI development team with adversarial validation loops. See `.kiro/steering/workflow.md` for the full pipeline.

## Agents

| Agent | Role | Focus |
|-------|------|-------|
| **Team Lead** | Orchestrator | Single point of contact, drives pipeline, assigns work |
| PM | Product Manager | Refines ideas into feature designs, validates deliverables |
| TW Expert | TW2002 Specialist | Game mechanics authority, validates game logic |
| Architect | Software Architect | Implementation plans, validates against codespecs |
| UI/UX | Interface Designer | TUI/HUD/CLI interface specs |
| Parser Expert | Log Parser Specialist | ANSI data stream analysis, pattern knowledge base |
| Builder | Implementer | Writes code + tests per architect's plan |

## Feature Artifacts

All artifacts for a feature live in `.kiro/skills/tw-team/features/NNN-slug/`:

```
features/NNN-slug/
├── design.md          # PM output
├── impl-plan.md       # Architect output
├── ui-spec.md         # UI/UX output
└── reviews/           # Adversarial review notes
```

## Shared Knowledge Base

`.kiro/skills/tw-team/knowledge/`:

- `parser-patterns/` — Game output formats, regex patterns, edge cases
- `tw-mechanics/` — Game rules, trading formulas, sector behavior
- `decisions/` — Architecture decisions, rejected approaches

Agents write discoveries here so knowledge persists across sessions.

## Session Data

Raw game session logs: `~/Documents/Games/TradeWars/sessions/` (`script -f` captures with ANSI escape codes).
