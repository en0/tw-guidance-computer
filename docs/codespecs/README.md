# Quality Code Specifications

Prescriptive standards for how new projects should be built. These are not records of past decisions — they are codified patterns for rapid development of small projects with rigorous code quality.

The focus is application development: servers, CLIs, consumers, data processors, one-shot scripts. Frameworks and libraries have different organizational needs and are not covered here.

## Values

- Complexity isolation — every piece of complexity has one home
- Inversion of control — depend on abstractions, not concretions
- Law of Demeter — talk to your friends, not your friends' friends
- One obvious place for everything — no ambiguity about where code lives
- No fat dependencies — understand what you import

## Specs

### Architecture

- [Hexagonal Architecture](Hexagonal-Architecture.md) — Three layers, strict dependency rule, domain at the center
- [Composition Root](Composition-Root.md) — Single wiring point, constructor injection, DI when justified
- [Use Case Pattern](Use-Case-Pattern.md) — One class per use case, application layer as explicit seam
- [Port Definitions](Port-Definitions.md) — Protocol-based ports, explicit adapter inheritance

### Domain

- [Domain Value Objects](Domain-Value-Objects.md) — Frozen dataclasses, validation in `__post_init__`, derived properties
- [Domain Exception Hierarchy](Domain-Exception-Hierarchy.md) — Flat hierarchy, bidirectional translation at adapter boundaries

### Testing

- [Testing Strategy](Testing-Strategy.md) — Mirror structure, one behavior per test, fixtures over setup/teardown
- [Mock Separation](Mock-Separation.md) — Creation, injection, and configuration as three separate concerns
- [Fixture Centralized Construction](Fixture-Centralized-Construction.md) — Factory fixtures with `setdefault` overrides

### Tooling

- [Project Tooling](Project-Tooling.md) — uv, src/ layout, pre-commit with ruff, mypy, and pytest
- [Typing Discipline](Typing-Discipline.md) — Strict mypy on source, `@final`, `@override`, relaxed tests
- [Minimal Dependencies](Minimal-Dependencies.md) — Small focused packages, prefer the standard library
