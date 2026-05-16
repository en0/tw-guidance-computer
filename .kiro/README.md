# AI Development Team

This project uses a team of specialized AI agents with adversarial validation loops.

## Quick Start

Your primary agent is **team-lead** (`/chat agent team-lead`). It orchestrates everything. You talk to it, it delegates to specialists internally.

For direct specialist access (rare — usually the team lead handles this):

| Agent | When to Use Directly |
|-------|---------------------|
| `ui-ux` | Working through interface design interactively |
| `parser-expert` | Debugging a specific parse failure with session data |

The team lead delegates to these internally — you don't normally switch:

| Agent | Role |
|-------|------|
| `pm` | Refines ideas into feature designs |
| `tw-expert` | Game mechanics authority |
| `architect` | Implementation planning, code validation |
| `builder` | Implements code + tests |

## Workflow

### Starting a new feature

```
/chat agent team-lead
```

Then describe what you want — use cases, pain points, rough ideas. The team lead handles everything from there.

### What happens next (you don't drive this — team lead does)

1. **Ideation** — Team lead delegates to PM + TW Expert. They refine your idea into a feature design with your use cases captured verbatim. Adversarial loop runs internally.
2. **Your approval** — Team lead presents the feature design. You approve or request changes.
3. **UI/UX** (if needed) — Team lead facilitates you working through the interface design with the UI/UX agent.
4. **Parser consultation** (if needed) — Parser Expert analyzes session logs for new patterns.
5. **Implementation planning** — Architect produces the build plan. Adversarial loop runs. If tradeoffs found, team lead asks you.
6. **Build** — Team lead creates `feature/NNN-slug` branch, spawns builders in parallel. Each builder commits, runs tests. Adversarial loop per builder.
7. **Validation** — Architect validates code against plan. PM validates against use cases. Team lead reports results.
8. **You approve** — "It's good." Team lead writes the CHANGELOG entry on the feature branch.
9. **You merge** — Merge the feature branch to main.
10. **You release** (separate decision) — Tag and release when ready. May bundle multiple features.

### Your approval gates (the only times you're asked)

- Feature design complete → approve or revise
- UI spec complete → approve or revise
- Tradeoffs discovered → accept or reject
- Validation complete → "good, merge it" (team lead writes CHANGELOG) or reject
- Release → your call, separate from merge

### Resuming a feature

If a session dies mid-pipeline, just start a new team-lead session. It checks `features/NNN-slug/` for existing artifacts and the STATUS field in `design.md` to pick up where it left off.

### Status values

| Status | Meaning |
|--------|---------|
| ideation | PM is refining the design |
| design | Design + UI approved, ready for planning |
| planning | Architect producing impl plan |
| building | Builders implementing |
| validating | Code complete, validation in progress |
| complete | All passed, ready for your merge |

## Feature Artifacts

`.kiro/skills/tw-team/features/NNN-slug/` — all docs for one feature live together:

```
features/001-threat-tracker/
├── design.md        # PM output
├── impl-plan.md     # Architect output
├── ui-spec.md       # UI/UX output
└── reviews/         # Adversarial review notes
```

Numbered for ordering, slugged for readability. See `features/README.md` for lifecycle.

## Knowledge Base

`.kiro/skills/tw-team/knowledge/` — persistent discoveries that survive session resets:

- `parser-patterns/` — How to parse specific game output
- `tw-mechanics/` — How the game actually works
- `decisions/` — Why things are built the way they are

Agents write here when they learn something. Read before you build.

## Templates

`.kiro/skills/tw-team/templates/` — Standard formats for handoff documents:

- `feature-design.md` — PM output (copied into `features/NNN-slug/design.md`)
- `impl-plan.md` — Architect output (copied into `features/NNN-slug/impl-plan.md`)
- `ui-spec.md` — UI/UX output (copied into `features/NNN-slug/ui-spec.md`)

## Session Data

Raw game logs: `~/traidwars/sessions/`
Debug samples: `~/traidwars/debug-sessions/`

Copy interesting session snippets into `debug-sessions/` for the parser expert to analyze.

## Structure

```
.kiro/
├── steering/
│   ├── team.md          # Team overview (always loaded)
│   └── workflow.md      # Pipeline and adversarial protocol (always loaded)
├── agents/
│   ├── pm.json
│   ├── tw-expert.json
│   ├── architect.json
│   ├── ui-ux.json
│   ├── parser-expert.json
│   ├── builder.json
│   └── prompts/         # System prompts for each agent
└── skills/
    └── tw-team/
        ├── SKILL.md
        ├── knowledge/   # Persistent discoveries
        ├── features/    # Feature artifacts (NNN-slug/ per feature)
        └── templates/   # Document templates
```
