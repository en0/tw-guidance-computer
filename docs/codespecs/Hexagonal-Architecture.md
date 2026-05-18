# Hexagonal Architecture (Ports & Adapters)

## Decision

All applications are structured into three layers — domain, application, and adapters — with a strict one-way dependency rule. The directory layout mirrors the architecture so there is exactly one obvious place for any piece of code.

This pattern applies to applications — servers, CLI tools, consumers, data processors. It does not apply to frameworks or libraries, which have different organizational needs (see "Scope" below).

## Why It Matters

When code is organized by technical concern (all models here, all services there, all utils in a junk drawer), it becomes unclear where new code belongs and easy to create hidden coupling. A feature change touches files scattered across the tree, and the dependency graph becomes a web.

Hexagonal architecture solves this by organizing around dependency direction. Each layer has a clear job, a clear set of allowed imports, and a clear boundary. When something breaks, the layer narrows the search space. When something new needs to be built, the layer tells you where to put it.

The directory layout enforcing the architecture is just as important as the architecture itself. If the structure doesn't make the rules visible, people (including future-you with bad memory) will violate them.

## Scope

This pattern applies to applications — servers, CLI tools, message consumers, data processors. These have a known composition root (the entry point that wires dependencies together), a fixed set of dependencies, and a clear boundary between business logic and I/O.

**Complexity threshold**: If an application has fewer than ~3 use cases and no external I/O beyond stdout, the full layer structure is overhead. A single module is fine. Apply this pattern when the application has enough moving parts that you'd otherwise lose track of what depends on what.

Frameworks and libraries have different organizational needs and are not the focus of these specs.

## Layers

### Domain (`domain/`)

Pure business logic. Zero external dependencies — no frameworks, no I/O, no third-party libraries that perform I/O or couple to external systems.

Pure computational libraries (e.g., a math library, a parser combinator) are acceptable in domain if they have no side effects and no I/O. The test is: does importing it create a dependency on an external system or runtime? If no, it's fine.

Contains:
- Value objects (immutable data with equality by value, e.g., frozen dataclasses) — see **Domain-Value-Objects.md**
- Domain entities — dataclasses with identity, lifecycle, and business behavior (state transitions, validation). Immutability preferred but not required. See **Domain-Entities.md**
- Domain exceptions
- Enums and type definitions

The domain layer knows nothing about how it's used, stored, or transported. It's not just data — it's the authoritative implementation of business rules that the application layer orchestrates.

### Application (`application/`)

Use cases and port definitions. Depends only on the domain layer.

Contains:
- Use cases — one class per business operation (see "Use Case Granularity" below)
- Ports (`application/ports/`) — abstract interfaces (Python `typing.Protocol` classes) describing what the application needs from the outside world

The application layer defines *what* external capabilities it needs (ports) but never *how* they're implemented. It imports domain types freely but never imports from adapters.

**Ports** are owned by the application layer because the application dictates what it needs — adapters conform to that contract, not the other way around. This keeps the dependency arrow pointing inward (adapters depend on application, not vice versa).

### Adapters (`adapters/`)

Implementations of ports and inbound interfaces. Depends on application and domain.

Contains:
- Outbound adapters — implement ports (REST clients, file I/O, database access, message producers)
- Inbound adapters — translate external input into use case calls (MCP tool registration, CLI argument parsing, HTTP handlers, message consumers)
- Configuration loaders

Adapters are the only layer that touches I/O libraries and external systems. All translation between the outside world and domain types happens here.

## Dependency Rule

```
adapters → application → domain
```

- Domain imports nothing from application or adapters.
- Application imports from domain. Never from adapters.
- Adapters import from application and domain.

This is enforced by convention, verified by code review, and should be backed by automated import linting in CI (e.g., `import-linter`, custom lint rules, or architecture test frameworks). If an import violates the direction, the code is in the wrong layer.

## Cross-Cutting Concerns

Logging, metrics, and tracing do not belong in domain. They are infrastructure concerns handled by adapters or injected via ports.

- **Logging**: Adapters log at boundaries. If a use case needs to emit structured events, define a port (e.g., `AuditLog`) rather than importing a logger.
- **Transactions**: Transaction boundaries are managed by the composition root or an adapter wrapping the use case. The use case itself is unaware of transaction mechanics.
- **Auth/authz**: Inbound adapters verify credentials before invoking use cases. The domain may define authorization *rules* (e.g., "only owners can delete"), but the enforcement mechanism lives in adapters.

## Error Propagation

- Domain defines its own exception hierarchy (e.g., `DomainError` base class).
- Application use cases raise domain exceptions or application-specific exceptions.
- Adapters catch adapter-specific errors (e.g., `requests.ConnectionError`) and translate them into domain exceptions before they cross the boundary.
- Inbound adapters catch domain/application exceptions and translate them into protocol-appropriate responses (HTTP status codes, CLI exit codes, etc.).

## Rules

1. **Directory layout mirrors the architecture.** Every application has `domain/`, `application/`, and `adapters/` directories under the package root.

2. **One obvious place for everything.** If you're writing a value object, it goes in `domain/`. If you're writing a use case, it goes in `application/`. If you're talking to an external system, it goes in `adapters/`. Boundary cases: DTOs that map between external formats and domain types live in adapters. Pure helper functions used only within one layer live in that layer.

3. **Ports live in `application/ports/`.** The application layer owns the interface definitions. Adapters implement them. This keeps the dependency arrow pointing inward.

4. **I/O and external-system libraries stay in adapters.** The domain and application layers never import `requests`, `boto3`, `pika`, `sqlalchemy`, or any library that performs I/O. Pure computational libraries without side effects (e.g., `dataclasses`, `re`, `decimal`) are allowed anywhere.

5. **The test directory mirrors the source directory.** `tests/test_domain/`, `tests/test_application/`, `tests/test_adapters/`. Unit test files map to source files. Integration and end-to-end tests live in `tests/integration/` or `tests/e2e/` — they don't need to mirror source structure.

6. **Inbound and outbound adapters are always separated.** `adapters/inbound/` contains handlers that translate external input into use case calls. `adapters/outbound/` contains implementations of ports. This makes the dependency direction visible in the directory structure — inbound adapters call use cases, outbound adapters implement ports.

## Use Case Granularity

"One class per business operation" means one use case per user-facing action or system event that the application handles. Signs a use case is too large: it has multiple public methods, or its `execute` method has branching paths that could be independent operations. Signs you're over-splitting: two use cases always run together and share all the same ports.

## Testing Philosophy

- **Domain tests**: Pure unit tests. No mocks needed — domain has no dependencies. Test business rules exhaustively.
- **Application tests**: Unit tests with mocked ports. Verify orchestration logic — that the use case calls the right ports with the right arguments.
- **Adapter tests**: Integration tests that verify the adapter correctly talks to the real external system (or a local substitute like testcontainers). These are slower and may be run separately.

## Directory Layout

```
src/package_name/
├── __init__.py
├── server.py | main.py | cli.py    # composition root: wires dependencies, starts the app
├── domain/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py              # re-exports: from .todo_item import TodoItem, etc.
│   │   ├── types.py                 # type aliases: SectorId = int, JobPath = str
│   │   ├── todo_item.py             # one model per file
│   │   ├── search_query.py
│   │   └── job_info.py
│   └── exceptions.py                # domain exception hierarchy
├── application/
│   ├── __init__.py
│   ├── some_use_case.py             # one file per use case
│   └── ports/
│       ├── __init__.py
│       └── some_client.py           # one file per port (typing.Protocol class)
└── adapters/
    ├── __init__.py
    ├── inbound/
    │   ├── __init__.py
    │   ├── mcp_tools.py             # translates external input into use case calls
    │   └── cli.py
    └── outbound/
        ├── __init__.py
        ├── some_rest_client.py      # implements a port
        └── config_loader.py
```

Consumers import `from my_app.domain.models import TodoItem` — the sub-module structure is invisible to the rest of the codebase because `__init__.py` re-exports all public types.

### Test directory (always mirrors source)

```
tests/
├── conftest.py                      # shared fixtures and factories
├── test_domain/
│   └── test_models.py
├── test_application/
│   └── test_some_use_case.py
├── test_adapters/
│   └── test_some_rest_client.py
└── integration/                     # cross-layer and external system tests
    └── test_search_flow.py
```

## Examples

### Import discipline in a use case

The use case imports from domain and from its own ports. Never from adapters.

```python
from my_app.domain.models import SearchQuery, SearchResult
from my_app.application.ports.search_client import SearchClient

@final  # prevents subclassing — use cases are concrete, not extension points
class RunQuery:
    def __init__(self, client: SearchClient) -> None:
        self._client = client

    def execute(self, query: SearchQuery) -> SearchResult:
        ...
```

### Import discipline in an adapter

The adapter imports from application (the port it implements) and domain (the types it translates to/from). It also imports the third-party library it wraps.

```python
import requests
from my_app.application.ports.search_client import SearchClient
from my_app.domain.models import SearchResult
from my_app.domain.exceptions import SearchError

@final
class SomeRestClient(SearchClient):
    def search(self, query: SearchQuery) -> SearchResult:
        try:
            response = requests.get(...)
            return SearchResult(...)  # translate to domain type
        except requests.ConnectionError as e:
            raise SearchError("search unavailable") from e  # translate to domain exception
```

### What never happens

```python
# WRONG: use case importing an adapter
from my_app.adapters.some_rest_client import SomeRestClient

# WRONG: domain importing a library that does I/O
import requests

# WRONG: domain importing from application
# (ports are owned by application because application defines what it needs;
#  domain doesn't know it's being orchestrated)
from my_app.application.ports.search_client import SearchClient
```
