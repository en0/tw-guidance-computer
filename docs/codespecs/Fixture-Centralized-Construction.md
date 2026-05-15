# Fixture-Centralized Construction with Marker-Driven Overrides

## Decision

All construction of the unit under test must happen in fixtures, never inline in test methods. Test-specific variations are declared via `pytest.mark` decorators, which fixtures read through `request.node.get_closest_marker()` to merge overrides into sane defaults.

## Why It Matters

When construction is scattered across test methods, every test becomes coupled to the constructor signature. A single parameter change — renaming an arg, adding a required dependency — forces edits across every test that constructs that object. Centralizing construction in a fixture creates a single point of change.

More importantly, it keeps test methods focused on what they're actually testing. A test body should express the scenario and the assertion, not plumbing. When setup noise lives in the method body, it's harder to see what the test is actually verifying.

## Rules

1. **Units under test are constructed in fixtures, not in test methods.** In the application, this is the composition root. In tests, it's fixtures.

2. **Fixtures provide sane defaults.** The fixture constructs the object with a default configuration that works for the common case. The happy-path test just requests the fixture and asserts.

3. **Test-specific variations use markers.** When a test needs to deviate from the default, it declares the deviation as a `@pytest.mark` decorator. The fixture reads the marker and merges overrides into the defaults before construction.

4. **Register custom markers in `pyproject.toml`** to avoid warnings and document intent.

5. **Scope determines placement.** If a fixture is used across multiple test files, it goes in `conftest.py`. If it's only used within one file, it stays local to that file.

6. **Factory fixtures are for value objects and entities, not units under test.** Domain models (value objects and entities) use factory fixtures that return callables — `make_search_query(limit=10)`. Units under test (use cases, adapters, clients) use direct fixtures that return the constructed object.

## Examples

### Use case fixture (local to test file)

The use case is constructed once in the fixture. Every test in the class gets the same wired-up instance.

```python
@pytest.fixture()
def trigger_build(mock_jenkins_client):
    return TriggerBuild(mock_jenkins_client)


class TestTriggerBuild:
    def test_trigger_without_params(self, trigger_build, mock_jenkins_client):
        result = trigger_build.execute("job/deploy")
        mock_jenkins_client.trigger_build.assert_called_once_with("job/deploy", None)
        assert "queue" in result.lower()
```

### Marker-driven config overrides

A default config is defined once. Tests declare only what they need to change.

```python
DEFAULT_CONFIG = {
    "crawl_delay": 0.5,
    "instances": {
        "infra": {"url": "https://jenkins.example.com", "user": "testuser", "token": "testtoken"},
    },
}


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
    def test_load_valid_config(self, config_loader):
        instances, delay = config_loader.load()
        assert "infra" in instances
        assert delay == 0.5

    @pytest.mark.config_overrides(crawl_delay=1.5)
    def test_custom_crawl_delay(self, config_loader):
        _, delay = config_loader.load()
        assert delay == 1.5
```

### Marker-driven mock responses

The adapter fixture reads a marker to pre-configure mock HTTP responses. Supports both `return_value` (status codes) and `side_effect` (connection errors) through the same marker.

```python
@pytest.fixture()
def patched_client(mock_session_get, mock_session_post, monkeypatch, request):
    client = JenkinsRestClient(base_url="http://jenkins.example.com", user="test", token="tok")
    monkeypatch.setattr(client._session, "get", mock_session_get)
    monkeypatch.setattr(client._session, "post", mock_session_post)
    marker = request.node.get_closest_marker("mock_response")
    if marker:
        kwargs = dict(marker.kwargs)
        side_effect = kwargs.pop("side_effect", None)
        if side_effect:
            mock_session_get.side_effect = side_effect
        else:
            mock_session_get.return_value = _mock_response(**kwargs)
    return client


class TestJenkinsRestClientErrors:
    @pytest.mark.mock_response(status_code=401)
    def test_401_raises_auth_error(self, patched_client):
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            patched_client.list_jobs()

    @pytest.mark.mock_response(side_effect=requests.exceptions.ConnectionError("refused"))
    def test_connection_error_raises(self, patched_client):
        with pytest.raises(JenkinsError, match="Request failed"):
            patched_client.list_jobs()

    @pytest.mark.mock_response(status_code=200, json_data={"jobs": [{"name": "build", "url": "http://x"}]})
    def test_successful_list_jobs(self, patched_client):
        entries = patched_client.list_jobs()
        assert len(entries) == 1
```

### Marker registration in pyproject.toml

```toml
[tool.pytest.ini_options]
markers = [
    "config_overrides: override default config values on ConfigLoader fixture",
    "mock_response: pre-configure mock GET response on patched_client fixture",
]
```

## When Inline Construction Is Acceptable

- **Value objects in scenario setup.** When a test configures mock return values with specific domain objects (`mock_client.list_jobs.return_value = [JobEntry(...)]`), that's the scenario description, not construction noise.
- **Intentionally broken construction.** Tests that verify behavior with a missing file, invalid path, or other error condition that prevents normal fixture setup.
