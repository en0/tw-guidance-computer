---
inclusion: always
---
# Development Workflow

## Pipeline

```
Ian ←→ Team Lead (single point of contact)
              │
              ├─ assigns to PM + TW Expert → Feature Design
              │       └─ adversarial loop (internal)
              │
              ├─ facilitates Ian ←→ UI/UX → Interface Spec
              │       └─ adversarial loop (internal)
              │
              ├─ assigns to Architect → Implementation Plan
              │       └─ adversarial loop (internal)
              │
              ├─ surfaces tradeoffs → Ian approves
              │
              ├─ spawns Builders (parallel) → Code + Tests
              │       └─ adversarial loop per builder (internal)
              │
              └─ assigns validation (Architect → PM) → reports to Ian
```

Ian only interacts at approval gates and when tradeoffs need decisions.

## Phases

### 1. Ideation (Ian → Team Lead → PM)
- Ian provides use cases, pain points, or rough ideas to Team Lead
- Team Lead assigns feature number, creates `features/NNN-slug/` directory
- Team Lead spawns PM sub-agent to refine into a feature design
- PM consults TW Expert (via Team Lead spawning sub-agent) for game mechanic accuracy
- Team Lead runs adversarial loop on the design internally
- Team Lead presents approved design to Ian for sign-off
- **Output**: Feature Design Document (`features/NNN-slug/design.md`)

### 2. UI/UX Design (Team Lead facilitates Ian ←→ UI/UX)
- Team Lead facilitates or hands off to UI/UX agent for interactive design work
- UI/UX produces interface spec for any HUD/TUI changes
- Team Lead runs adversarial loop on the UI spec
- Ian approves the interface
- If no UI changes needed, this phase is skipped
- **Output**: UI Spec (`features/NNN-slug/ui-spec.md`)

### 2b. Parser Consultation (if new data requirements identified)
- Team Lead spawns Parser Expert sub-agent to analyze session data for required patterns
- Parser Expert documents findings in `knowledge/parser-patterns/`
- Team Lead runs adversarial loop on parser findings (validates regex accuracy, edge cases)
- Findings feed into the Architect's implementation plan
- **Output**: Knowledge base entries

### 3. Implementation Planning (Team Lead → Architect)
- Team Lead spawns Architect sub-agent with approved design + UI spec + parser findings
- Architect produces implementation plan with work units and parallel groups
- Architect validates against codespecs
- Team Lead runs adversarial loop on the plan
- If tradeoffs or simplifications found, Team Lead surfaces to Ian for approval
- **Output**: Implementation Plan (`features/NNN-slug/impl-plan.md`)

### 4. Build (Team Lead → Builders)
- Team Lead spawns Builder sub-agents per parallel work group
- Each builder produces code + tests
- Each builder follows the implementation plan exactly
- Team Lead runs adversarial loop per builder
- If a builder discovers a conflict with another work unit, escalate to Architect
- **Output**: Code + tests per work unit

### 5. Validation (Team Lead → Architect → PM → Ian)
- Team Lead spawns Architect sub-agent: validate all code against plan and codespecs
- Team Lead spawns PM sub-agent: validate against feature design and use cases
- Architect FAIL → issues back to builders for revision
- PM FAIL → escalate to Architect to revise plan, then rebuild
- Max 2 revision cycles before escalating to Ian
- Team Lead reports results to Ian for final sign-off

## Adversarial Loop (applies at every phase)

```
Agent (Creator Mode)
    │
    ▼ produces deliverable
    │
Agent (Adversary Mode) ← fresh instance, same role
    │
    ▼ scrutinizes output
    │
    ├─ PASS → deliverable moves to next phase
    └─ FAIL → findings go back to creator for revision
```

### Adversary Rules
- The adversary has NO memory of the creation process
- The adversary's job is to find flaws, not to be helpful
- The adversary validates against: role-specific rules, codespecs, consistency, completeness
- The adversary produces a verdict: PASS (with notes) or FAIL (with specific issues)
- Maximum 2 revision cycles before escalating to Ian

## Knowledge Base Updates

Any agent that discovers something about the data stream, game mechanics, or architecture MUST write it to the appropriate knowledge file before completing their task. Knowledge is never lost to session boundaries.

## Git Branching

- Team Lead creates a feature branch at the start of Phase 4 (Build): `feature/NNN-slug`
- All builder work happens on this branch
- Agents NEVER merge to main, tag, or release
- Ian merges, tags, and releases when satisfied after final validation
- Design artifacts (`.kiro/` changes from Phases 1-3) may be committed to main directly — they're documentation, not code
