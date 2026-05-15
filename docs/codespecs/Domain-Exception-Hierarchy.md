# Domain Exception Hierarchy

## Decision

Every application defines a small, flat exception hierarchy rooted in a single base exception. Exceptions are domain concepts, not technical artifacts. The adapter boundary is where exception translation happens in both directions — outbound adapters translate third-party exceptions into domain exceptions, and inbound adapters translate domain exceptions into framework-appropriate responses. No exception crosses the boundary without translation.

## Why It Matters

When third-party exceptions propagate freely, callers end up catching `requests.HTTPError` or `psycopg2.OperationalError` in business logic. That couples the application to implementation details of adapters it's not supposed to know about. Swapping an adapter means changing every `except` block that caught its exceptions.

The same problem exists in the other direction. If a use case raises a framework-level exception — an HTTP 404, a Flask `abort`, a Click `UsageError` — the application layer is now coupled to the transport. You can't reuse that use case behind a different inbound adapter without dragging the framework along. The use case should raise `JobNotFoundError` and have no idea whether that becomes a 404, an error string in an MCP response, or a non-zero exit code. That translation is the inbound adapter's job.

A domain exception hierarchy gives both sides a shared vocabulary. Outbound adapters translate *into* it. Inbound adapters translate *out of* it. The application and domain layers only ever see domain exceptions — they don't know what produced them or what will consume them.

Keeping the hierarchy small and flat matters too. Deep exception trees with dozens of leaves create the same "where does this go" problem that hexagonal architecture solves for code. If you need a new exception, it should be obvious where it fits. If it's not obvious, the hierarchy is too complex.

## Rules

1. **One base exception per application.** It extends `Exception` directly. Every other domain exception extends this base. Callers who want a catch-all for the application's errors catch the base.

2. **Keep the hierarchy flat.** One level of inheritance below the base is the default. Deeper nesting is a code smell — it usually means you're encoding technical details (HTTP status codes, retry categories) rather than domain concepts.

3. **Exceptions describe domain problems, not technical ones.** `JobNotFoundError` — yes. `Http404Error` — no. `QueryValidationError` — yes. `JsonDecodeError` — no.

4. **Adapters translate all external exceptions.** Every `try/except` in an adapter catches the third-party exception and raises a domain exception with `from` to preserve the chain. No `requests.ConnectionError`, no `yaml.YAMLError`, no `json.JSONDecodeError` ever crosses the adapter boundary.

5. **Use `raise ... from e` to preserve the exception chain.** The domain exception is what callers see. The original exception is available via `__cause__` for debugging. Never swallow the original.

6. **Exceptions live in `domain/exceptions.py`.** One file. If you have so many exceptions that this file is hard to navigate, the hierarchy is probably too large.

## Examples

### Exception hierarchy

```python
class JenkinsError(Exception):
    """Base exception for all Jenkins domain errors."""

class AuthenticationError(JenkinsError):
    """Raised when authentication fails."""

class JobNotFoundError(JenkinsError):
    """Raised when a job or build is not found."""

class BuildTriggerError(JenkinsError):
    """Raised when a build trigger request fails."""
```

### Adapter translating third-party exceptions

```python
def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
    try:
        resp = self._session.request(method, f"{self._base_url}{path}", **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status in (401, 403):
            raise AuthenticationError(f"Authentication failed ({status})") from e
        if status == 404:
            raise JobNotFoundError(f"Not found: {path}") from e
        raise AppError(f"API request failed ({status}): {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise AppError(f"Connection failed: {e}") from e
    except requests.exceptions.RequestException as e:
        raise AppError(f"Request failed: {e}") from e
```

Every branch raises a domain exception. Every raise uses `from e`. Nothing from `requests` escapes.

### Inbound adapter translating domain exceptions out

Inbound adapters (HTTP handlers, MCP tools, CLI entrypoints) catch domain exceptions and translate them into whatever the framework expects. The translation goes the other direction — domain vocabulary out to framework vocabulary.

```python
# Flask handler catching domain exceptions
@app.route("/jobs/<path:job_path>")
def get_job(job_path: str):
    try:
        info = get_job_info.execute(job_path)
        return jsonify(info)
    except JobNotFoundError:
        abort(404)
    except AuthenticationError:
        abort(403)
    except AppError as e:
        abort(500, description=str(e))
```

```python
# MCP tool catching domain exceptions
@mcp.tool()
def get_job_info(job_path: str) -> str:
    try:
        info = use_case.execute(job_path)
        return json.dumps({"name": info.name})
    except AppError as e:
        return f"Error: {e}"
```

### What never happens

```python
# WRONG: use case catching a third-party exception
try:
    result = self._client.fetch(query)
except requests.exceptions.HTTPError:
    ...

# WRONG: adapter letting a third-party exception propagate
def fetch(self, query):
    resp = self._session.get(url)  # ConnectionError can escape
    resp.raise_for_status()        # HTTPError can escape
    return resp.json()             # JSONDecodeError can escape
```
