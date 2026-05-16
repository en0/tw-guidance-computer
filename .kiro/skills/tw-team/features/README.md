# Features

Each feature request gets a numbered directory containing all artifacts from the pipeline.

## Naming Convention

`NNN-slug/` — three-digit number + kebab-case slug.

```
features/
├── 001-threat-tracker/
│   ├── design.md          # PM: feature design document
│   ├── impl-plan.md       # Architect: implementation plan
│   ├── ui-spec.md         # UI/UX: interface specification
│   └── reviews/           # Adversarial review notes per phase
│       ├── design-review.md
│       ├── impl-review.md
│       └── ui-review.md
└── 002-sector-activity-log/
    └── ...
```

## Lifecycle

1. PM creates `design.md` from template
2. Adversary reviews → `reviews/design-review.md`
3. Architect creates `impl-plan.md`
4. Adversary reviews → `reviews/impl-review.md`
5. UI/UX creates `ui-spec.md` (if applicable)
6. Adversary reviews → `reviews/ui-review.md`
7. Builders implement from `impl-plan.md`
8. Feature complete → no further changes to this directory

## Status Tracking

The Team Lead maintains the `STATUS` line at the top of `design.md` and updates it at each phase transition:

```
STATUS: ideation | design | planning | building | validating | complete
```

| Status | Meaning |
|--------|---------|
| ideation | PM is refining the design |
| design | Design + UI spec approved by user, ready for planning |
| planning | Architect is producing impl plan |
| building | Builders are implementing |
| validating | Code complete, validation in progress |
| complete | All validation passed, ready for user merge |
