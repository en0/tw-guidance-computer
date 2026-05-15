# Testing Strategy

## Decision

Tests mirror the source directory structure. Each test targets exactly one behavior. There is no setup/teardown ceremony — all construction happens in fixtures, all variation happens through markers, and test methods contain only the scenario and the assertion.

## Why It Matters

Tests are the first thing to rot when they're hard to write or hard to read. If adding a test requires boilerplate setup, people skip it. If reading a test requires tracing through inheritance hierarchies or shared mutable state, people stop trusting the suite.

The goal is tests that are obvious: you look at the test method and immediately see what's being tested, what the inputs are, and what's expected. Everything else — construction, wiring, mock configuration — lives in fixtures where it's defined once and reused.

Mirroring the source structure means you never have to guess where a test lives. `src/app/application/trigger_build.py` → `tests/test_application/test_trigger_build.py`. The mapping is mechanical.

## Rules

1. **Test directory mirrors source.** `test_domain/`, `test_application/`, `test_adapters/`. Each test file maps to a source file.

2. **Each test targets one behavior.** Not one method — one behavior. A method with three interesting code paths gets three tests, not one test with three asserts.

3. **Test methods contain scenario and assertion only.** No construction, no wiring, no mock setup. If you see `SomeClass(dep1, dep2, dep3)` in a test method, it belongs in a fixture. See **Fixture-Centralized-Construction.md**.

4. **Use `monkeypatch` for patching, not `unittest.mock.patch` decorators.** `monkeypatch` is explicit, scoped to the test, and doesn't require understanding decorator stacking order.

5. **`pytest.mark` for test-specific variation.** When a test needs different configuration, mock responses, or construction parameters, declare it as a marker. The fixture reads the marker and adjusts. The test method stays clean.

6. **Shared fixtures in `conftest.py`, local fixtures in the test file.** Factory fixtures for value objects and shared mocks go in the root `conftest.py`. Fixtures specific to one test file (use case construction, adapter patching) stay local.

7. **No docstrings on test methods.** The test name and the code are the documentation. If a test needs a comment to explain what it's doing, it's too complex.

8. **No setup/teardown methods.** No `setUp`, no `tearDown`, no `setUpClass`. Fixtures handle all of this with proper scoping.

9. **Group related tests in classes.** `class TestTriggerBuild:` groups all tests for that use case. The class is just an organizational tool — no shared state, no inheritance.

## Examples

### Use case test — mock port, assert behavior

```python
@pytest.fixture()
def search_jobs(mock_job_cache):
    return SearchJobs(mock_job_cache)

class TestSearchJobs:
    def test_finds_match(self, search_jobs):
        results = search_jobs.execute("infra", "deploy")
        assert len(results) == 1
        assert results[0].name == "deploy"

    def test_case_insensitive(self, search_jobs):
        results = search_jobs.execute("infra", "DEPLOY")
        assert len(results) == 1

    def test_empty_cache_returns_empty(self, search_jobs, mock_job_cache):
        mock_job_cache.load.return_value = None
        results = search_jobs.execute("infra", "deploy")
        assert results == []
```

### Use case test — verifying delegation

```python
@pytest.fixture()
def trigger_build(mock_client):
    return TriggerBuild(mock_client)

class TestTriggerBuild:
    def test_delegates_to_client(self, trigger_build, mock_client):
        result = trigger_build.execute("job/deploy")
        mock_client.trigger_build.assert_called_once_with("job/deploy", None)
        assert "queue" in result.lower()

    def test_passes_parameters(self, trigger_build, mock_client):
        params = {"BRANCH": "develop"}
        trigger_build.execute("job/deploy", params)
        mock_client.trigger_build.assert_called_once_with("job/deploy", params)
```

### Adapter test — marker-driven mock responses

```python
class TestRestClientErrors:
    @pytest.mark.mock_response(status_code=401)
    def test_401_raises_auth_error(self, patched_client):
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            patched_client.list_jobs()

    @pytest.mark.mock_response(status_code=404)
    def test_404_raises_not_found(self, patched_client):
        with pytest.raises(JobNotFoundError):
            patched_client.get_job_info("job/missing")

    @pytest.mark.mock_response(status_code=200, json_data={"jobs": [{"name": "build"}]})
    def test_successful_response(self, patched_client):
        entries = patched_client.list_jobs()
        assert len(entries) == 1
```

### Domain test — validation enforcement

```python
class TestSearchQuery:
    def test_empty_query_raises(self, make_search_query):
        with pytest.raises(QueryValidationError, match="must not be empty"):
            make_search_query(query="   ")

    def test_zero_limit_raises(self, make_search_query):
        with pytest.raises(QueryValidationError, match="limit"):
            make_search_query(limit=0)
```

### Marker-driven adapter configuration

```python
@pytest.fixture()
def config_loader(tmp_path, request):
    config = {**DEFAULT_CONFIG}
    marker = request.node.get_closest_marker("config_overrides")
    if marker:
        config.update(marker.kwargs)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(config))
    return ConfigLoader(config_path=path)

class TestConfigLoader:
    def test_loads_default_config(self, config_loader):
        instances, delay = config_loader.load()
        assert "infra" in instances
        assert delay == 0.5

    @pytest.mark.config_overrides(crawl_delay=1.5)
    def test_custom_crawl_delay(self, config_loader):
        _, delay = config_loader.load()
        assert delay == 1.5
```
