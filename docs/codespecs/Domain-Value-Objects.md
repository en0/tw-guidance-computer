# Domain Value Objects

## Decision

All domain value objects are frozen dataclasses. They validate their own invariants at construction time via `__post_init__`. They carry no behavior beyond derived properties. They are never marked `@final`. For domain models with identity, lifecycle, or business behavior (state transitions, business rules), see **Domain-Entities.md**.

## Why It Matters

Value objects are the shared language of the application. Use cases pass them around, adapters translate to and from them, tests assert against them. If they're mutable, any code holding a reference can silently change state that other code depends on. If they don't self-validate, invalid state leaks through the system and surfaces as confusing errors far from the source.

Frozen dataclasses solve both problems. Immutability means no spooky action at a distance. `__post_init__` validation means invalid objects can't exist — construction either succeeds with a valid object or raises immediately.

## Rules

1. **`@dataclass(frozen=True)` for all value objects.** No exceptions. Immutability is not optional for value objects.

2. **Every value object validates in `__post_init__`.** All fields with meaningful constraints (non-empty, positive, valid range, non-negative) must be enforced at construction time. This applies regardless of how or where the object is constructed — the domain layer does not know its callers and cannot assume valid input. Value objects are part of the domain's public interface; any code (adapters, use cases, tests, future modules) can construct them. Raise a domain exception on failure — never let an invalid object exist. See **Domain-Exception-Hierarchy.md**.

3. **Do not mark value objects with `@final`.** There's no hidden mutable state to protect. Subclassing a frozen dataclass is safe and sometimes useful.

4. **Derived properties are fine.** Read-only `@property` methods that compute values from the object's fields belong on the value object. They're pure functions of immutable state.

5. **Use `field(default_factory=list)` for mutable default types.** Standard dataclass hygiene — never use a mutable literal as a default.

6. **Enums live in the domain layer alongside value objects.** They're part of the domain vocabulary.

7. **Type aliases live in `domain/models/types.py`.** Simple named types (e.g., `SectorId = int`, `JobPath = str`) that add semantic clarity without needing validation. One file for all aliases. `__init__.py` re-exports them alongside value objects.

8. **Value objects live in `domain/models/`, one file per model.** The `domain/models/` sub-module has one file per value object (or per tightly-coupled group). `__init__.py` re-exports all public types so consumers import `from my_app.domain.models import SearchQuery`. See **Hexagonal-Architecture.md** for the directory layout.

9. **Factory fixtures for testing.** Value objects are constructed via factory fixtures that return callables with sane defaults. Tests override only the fields relevant to the scenario. See **Fixture-Centralized-Construction.md**.

## Examples

### Value object with validation

```python
@dataclass(frozen=True)
class SearchQuery:
    query: str
    from_time: str
    to_time: str
    limit: int = 100

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise QueryValidationError("Query must not be empty")
        if self.limit < 1:
            raise QueryValidationError("limit must be >= 1")
```

### Value object with derived property

```python
@dataclass(frozen=True)
class SearchResult:
    status: SearchStatus
    records: list[dict[str, str]]
    messages: list[dict[str, str]]

    @property
    def is_aggregate(self) -> bool:
        return self.status.record_count > 0

    @property
    def items(self) -> list[dict[str, str]]:
        return self.records if self.is_aggregate else self.messages
```

### Value object with composition

```python
@dataclass(frozen=True)
class JobInfo:
    name: str
    description: str = ""
    parameters: list[BuildParameter] = field(default_factory=list)
    last_build: BuildStatus | None = None
```

### Enum in the domain

```python
class JobState(Enum):
    GATHERING = "GATHERING RESULTS"
    DONE = "DONE GATHERING RESULTS"
    CANCELLED = "CANCELLED"
```

### Factory fixture for testing

```python
@pytest.fixture()
def make_search_query():
    def _factory(**kwargs):
        kwargs.setdefault("query", "* | count by _sourceCategory")
        kwargs.setdefault("from_time", "2024-01-01T00:00:00Z")
        kwargs.setdefault("to_time", "2024-01-02T00:00:00Z")
        kwargs.setdefault("limit", 100)
        return SearchQuery(**kwargs)
    return _factory
```

### Test using factory fixture

```python
class TestSearchQuery:
    def test_valid_query(self, make_search_query):
        q = make_search_query()
        assert q.query == "* | count by _sourceCategory"

    def test_empty_query_raises(self, make_search_query):
        with pytest.raises(QueryValidationError, match="must not be empty"):
            make_search_query(query="   ")

    def test_custom_values(self, make_search_query):
        q = make_search_query(query="error", limit=10)
        assert q.query == "error"
        assert q.limit == 10
```
