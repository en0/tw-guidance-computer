# Port Definitions

## Decision

Ports are defined as `typing.Protocol` classes in `application/ports/`. They describe what the application layer needs from the outside world without specifying how it's provided. Adapters explicitly inherit from the Protocol they implement. One file per port.

## Why It Matters

Ports are the boundary contract between the application and everything external. Without them, use cases either import adapters directly (coupling to implementation) or rely on implicit duck typing (no visible contract, no IDE support, no documentation of what's expected).

A Protocol makes the contract explicit and visible. The application layer says "I need something that can do X, Y, Z" without knowing or caring what provides it. The adapter says "I implement X, Y, Z" by inheriting from the Protocol. The composition root connects them.

Explicit inheritance (rather than relying on structural matching alone) makes the relationship visible to both humans and tools. If an adapter claims to implement a port, the type checker verifies it. If a method signature drifts, mypy catches it.

## Rules

1. **Ports are `typing.Protocol` classes.** This is the standard for applications. They define method signatures, argument types, return types, and document which domain exceptions may be raised.

2. **Adapters explicitly inherit from the Protocol.** `class SomeRestClient(SearchClient)` — not just structural compatibility. This makes the relationship visible and type-checker-verifiable.

3. **Ports live in `application/ports/`, one file per port.** The application layer owns the interface. Adapters depend on it, not the other way around.

4. **Ports speak domain types.** Parameters and return types are domain value objects, not primitives from third-party libraries. A port never exposes `requests.Response` or `psycopg2.cursor` — it exposes `SearchResult` or `list[JobEntry]`.

5. **Ports document their exception contract.** The `Raises:` section in docstrings lists which domain exceptions callers should expect. This is part of the interface.

6. **Use `@override` on every method that implements a port.** This makes it explicit which methods fulfill the contract and catches signature mismatches.

7. **ABC is an alternative for frameworks.** When building a framework where consumers implement the interface, `abc.ABC` with `@abstractmethod` provides stronger enforcement — you can't instantiate an incomplete implementation. Protocol is preferred for applications; ABC is appropriate when the interface is part of a public API that external code implements.

## Examples

### Port definition

```python
from typing import Protocol
from my_app.domain.models import SearchQuery, SearchResult, SearchStatus

class SearchClient(Protocol):
    def create_job(self, query: SearchQuery) -> str:
        """Create a search job and return its ID.

        Args:
            query (SearchQuery): The search query to execute.

        Returns:
            str: The search job ID.

        Raises:
            AppError: If the API request fails.
        """
        ...

    def get_status(self, job_id: str) -> SearchStatus:
        ...

    def get_results(self, job_id: str, query: SearchQuery) -> SearchResult:
        ...
```

### Adapter implementing a port

```python
from typing import final, override
from my_app.application.ports.search_client import SearchClient

@final
class SomeRestClient(SearchClient):
    def __init__(self, base_url: str) -> None:
        self._session = requests.Session()
        self._base_url = base_url

    @override
    def create_job(self, query: SearchQuery) -> str:
        ...

    @override
    def get_status(self, job_id: str) -> SearchStatus:
        ...

    @override
    def get_results(self, job_id: str, query: SearchQuery) -> SearchResult:
        ...
```

### Use case depending on a port

The use case accepts the Protocol type. It never knows which adapter is behind it.

```python
@final
class RunQuery:
    def __init__(self, client: SearchClient) -> None:
        self._client = client

    def execute(self, query: SearchQuery) -> SearchResult:
        job_id = self._client.create_job(query)
        ...
```

### Mocking a port in tests

`MagicMock(spec=Protocol)` gives you a mock that satisfies the type and catches calls to methods that don't exist on the port.

```python
@pytest.fixture()
def mock_client():
    return MagicMock(spec=SearchClient)
```
