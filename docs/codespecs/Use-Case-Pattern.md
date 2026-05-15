# Use Case Pattern

## Decision

Each business operation is a single class with one public method: `execute()`. The class receives its dependencies through the constructor (ports, configuration values) and is marked `@final`. Use cases live in the application layer — one file per use case.

## Why It Matters

In classic three-layer architectures (presentation/business/data), there's no explicit seam between business logic and the layers that call it or that it calls. Orchestration code — the glue that coordinates domain logic with external concerns — ends up scattered across presentation, business, and sometimes even the data layer. The result is that business logic becomes indirectly coupled to adapters, even when no one intended it.

The application layer is that missing seam. Its sole responsibility is orchestrating domain logic and adapter interactions for a particular use case. It's thin glue — it doesn't contain business rules (those live in the domain) and it doesn't talk to external systems directly (those are behind ports). It just wires the two together for a specific operation.

One class per use case keeps this glue focused. Each class has exactly the dependencies it needs — no more. Tests construct only what they're testing. New operations are new files. The dependency list on the constructor is a precise manifest of what this operation requires from the outside world.

Marking use cases `@final` prevents subclassing, which protects the private state and keeps the execution path obvious. There's one implementation, one `execute()` method, one place to look when something goes wrong.

## Rules

1. **One class per use case, one file per class.** The file name matches the operation: `trigger_build.py` contains `TriggerBuild`, `run_query.py` contains `RunQuery`.

2. **One public method: `execute()`.** This is the entry point. The caller doesn't need to know anything about the class beyond its constructor signature and `execute()`.

3. **Dependencies are injected via the constructor.** Ports, configuration values, other use cases if needed. Never constructed internally.

4. **Mark with `@final`.** Use cases have private state (the injected dependencies). Subclassing could corrupt that. Prevent it.

5. **Use cases only import from domain and application.** They depend on ports (Protocols) and domain types. Never on adapters, never on third-party libraries.

6. **Private helper methods are fine.** If `execute()` gets long, extract private methods. They're implementation details of the use case, not part of the public interface.

7. **Configuration values are constructor parameters, not hardcoded.** Poll intervals, timeouts, delays — anything that might vary between environments or tests is injected. Provide sensible defaults.

## Examples

### Thin delegation — use case as a seam

The simplest case: the use case just delegates to a port. It exists as a seam for testing and to maintain the pattern.

```python
@final
class TriggerBuild:
    def __init__(self, client: JenkinsClient) -> None:
        self._client = client

    def execute(self, job_path: str, parameters: dict[str, str] | None = None) -> str:
        return self._client.trigger_build(job_path, parameters)
```

### Orchestration — use case coordinating multiple steps

```python
@final
class RunQuery:
    def __init__(
        self,
        client: SearchClient,
        poll_interval: float = 2.0,
        poll_timeout: float = 300.0,
    ) -> None:
        self._client = client
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout

    def execute(self, query: SearchQuery) -> SearchResult:
        job_id = self._client.create_job(query)
        self._poll_until_done(job_id)
        return self._client.get_results(job_id, query)

    def _poll_until_done(self, job_id: str) -> None:
        deadline = time.monotonic() + self._poll_timeout
        while time.monotonic() < deadline:
            status = self._client.get_status(job_id)
            if status.state == JobState.DONE:
                return
            if status.state in (JobState.CANCELLED, JobState.FORCE_PAUSED):
                raise SearchJobError(f"Job {job_id} ended with state: {status.state.value}")
            time.sleep(self._poll_interval)
        raise SearchTimeoutError(f"Job {job_id} timed out after {self._poll_timeout}s")
```

### Application-layer logic — filtering, transforming

```python
@final
class SearchJobs:
    def __init__(self, cache: JobCache) -> None:
        self._cache = cache

    def execute(self, instance_name: str, query: str) -> list[JobEntry]:
        entries = self._cache.load(instance_name)
        if entries is None:
            return []
        query_lower = query.lower()
        return [e for e in entries if query_lower in e.name.lower()]
```

### Testing a use case

The use case is constructed in a fixture with a mock port. The test exercises `execute()` and asserts on the result or the mock interaction.

```python
@pytest.fixture()
def trigger_build(mock_client):
    return TriggerBuild(mock_client)

class TestTriggerBuild:
    def test_delegates_to_client(self, trigger_build, mock_client):
        result = trigger_build.execute("job/deploy")
        mock_client.trigger_build.assert_called_once_with("job/deploy", None)
        assert result is not None
```
