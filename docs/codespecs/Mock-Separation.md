# Mock Separation

## Decision

Mock setup has three distinct concerns — creation, injection, and configuration — and each one is handled by a separate mechanism. Creation is a fixture. Injection is a fixture that uses `monkeypatch`. Configuration is either a marker or an explicit line in the test body. They never collapse into one thing.

## Why It Matters

When mock setup is inlined in test methods, every test repeats the same construction and patching boilerplate. When it's all collapsed into one fixture, the fixture becomes a god object that tries to anticipate every scenario. Both paths lead to tests that are hard to read and hard to change.

Separating the three concerns means each test method shows only what's different about that scenario. Creation and injection are solved once and reused. Configuration — the only part that varies per test — stays where the reader can see it.

## Rules

### Creation

1. **Mock creation fixtures produce a ready-to-use mock with sensible defaults.** Every method on the mock returns a valid domain object. Tests that don't care about a specific method's return value never have to think about it.

2. **Mock creation fixtures accept overrides.** The same `kwargs` override pattern used by factory fixtures (see Fixture-Centralized-Construction.md) applies here. A test that needs a specific return value passes it in; everything else keeps its default.

3. **Response helpers are plain functions, not fixtures.** A helper that builds a configured HTTP response object is a module-level function. It has no pytest lifecycle — it's just a constructor.

### Injection

4. **Injection fixtures construct the real object and replace its dependencies.** This is the only place `monkeypatch` appears. The fixture builds the real adapter or use case, swaps in the mock, and returns the real object. Tests call the real object, not the mock — the mock is only referenced directly to assert interactions or override configuration.

5. **Injection fixtures can read markers.** When the injection fixture sees a marker on the test, it uses it to pre-configure the mock before returning. This keeps repetitive adapter test patterns declarative — the test body contains only the call and the assertion.

### Configuration

6. **Use markers for repetitive patterns.** When every test in a class follows the same shape — configure response, call method, assert result — declare the varying part as a marker. The injection fixture reads it and does the wiring.

7. **Use explicit configuration when the test needs control.** When a test needs to configure the mock mid-test, or the setup doesn't fit a marker, pull the creation fixture into the test signature and set `.return_value` or `.side_effect` directly.

## Examples

### Mock creation with override support

```python
@pytest.fixture()
def mock_search_client(request):
    client = MagicMock(spec=SearchClient)
    marker = request.node.get_closest_marker("mock_client")
    overrides = marker.kwargs if marker else {}

    client.create_job.return_value = overrides.get("create_job", "JOB123")
    client.get_status.return_value = overrides.get(
        "get_status",
        SearchStatus(job_id="JOB123", state=JobState.DONE),
    )
    client.get_results.return_value = overrides.get(
        "get_results",
        SearchResult(status=SearchStatus(job_id="JOB123", state=JobState.DONE), items=[{"_raw": "log line"}]),
    )
    return client
```

### Injection with marker-driven responses

```python
def _mock_response(status_code, json_data=None, side_effect=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp

@pytest.fixture()
def mock_session():
    return MagicMock()

@pytest.fixture()
def patched_client(mock_session, monkeypatch, request):
    client = RestClient(base_url="http://example.com", token="tok")
    monkeypatch.setattr(client._session, "get", mock_session)
    marker = request.node.get_closest_marker("mock_response")
    if marker:
        kwargs = dict(marker.kwargs)
        side_effect = kwargs.pop("side_effect", None)
        if side_effect:
            mock_session.side_effect = side_effect
        else:
            mock_session.return_value = _mock_response(**kwargs)
    return client

class TestRestClientErrors:
    @pytest.mark.mock_response(status_code=401)
    def test_401_raises_auth_error(self, patched_client):
        with pytest.raises(AuthenticationError):
            patched_client.list_items()

    @pytest.mark.mock_response(status_code=200, json_data={"items": [{"name": "a"}]})
    def test_successful_response(self, patched_client):
        items = patched_client.list_items()
        assert len(items) == 1
```

### Explicit configuration in the test body

```python
class TestRestClientErrors:
    def test_connection_error(self, patched_client, mock_session):
        mock_session.side_effect = requests.exceptions.ConnectionError("refused")
        with pytest.raises(ApiError, match="Connection failed"):
            patched_client.create_job(query)
```

### Use case wiring with mock override

```python
@pytest.fixture()
def run_query(mock_search_client):
    return RunQuery(client=mock_search_client)

class TestRunQuery:
    def test_returns_results(self, run_query):
        result = run_query.execute(query)
        assert result.items == [{"_raw": "log line"}]

    @pytest.mark.mock_client(get_status=SearchStatus(job_id="X", state=JobState.GATHERING))
    def test_polls_until_done(self, run_query, mock_search_client):
        # get_status was overridden via marker — stays GATHERING
        ...
```
