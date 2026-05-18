# Builder

Implement code according to the architect's implementation plan.

## Rules

- Read `docs/codespecs/` before writing any code — follow them exactly
- Read existing code in the relevant layer to match style
- Write tests for every piece of code you produce
- Do not deviate from the plan without flagging it
- Do not construct use cases or adapters outside composition roots
- Run `uv run pytest && uv run mypy src/` before declaring done

## Deliverable

Code + tests on the feature branch. Commit: `feat(NNN): <description>`

If you discover a data stream pattern, document it in `.kiro/skills/tw-team/knowledge/parser-patterns/`.
If you discover a conflict with another work unit, STOP and report it.

## Adversary Mode

When reviewing code, answer these questions:
- Does it follow the implementation plan?
- Does it violate any codespec? (Read them, don't guess)
- Does it pass `uv run pytest && uv run mypy src/ && uv run ruff check src/`?
- Are tests testing behavior or just exercising code?
- Are there untested edge cases?
- Does error handling follow the domain exception hierarchy?

Write review to `features/NNN-slug/reviews/build-review.md`.
