# Typing Discipline

## Decision

Source code is fully type-annotated and runs strict mypy. Tests get a relaxed override. `@final` marks classes that are not extension points. `@override` marks every method that implements or overrides a parent. Unused return values are assigned to `_`.

## Why It Matters

Type annotations are a contract. Strict checking on source code catches mismatches at lint time instead of runtime — wrong argument types, missing return annotations, untyped function signatures. But applying the same strictness to tests creates friction with no payoff: test fixtures, mock setup, and parametrize decorators fight the type checker constantly.

`@final` and `@override` make intent explicit. When a class is `@final`, the reader knows it's a leaf — no one subclasses it, and the type checker enforces that. When a method is `@override`, the reader knows it's implementing a contract, and the type checker verifies the parent actually defines that method.

## Rules

### Mypy Configuration

1. **Strict mode on source, relaxed on tests.** `strict = true` in the mypy config. A `tests.*` override disables `disallow_untyped_defs` and `disallow_untyped_calls`. Everything else stays strict for tests.

2. **Every function in source has full annotations.** Parameters, return types, no exceptions. If a function returns nothing, annotate `-> None`.

### @final

3. **Mark stateful classes `@final`.** Use cases, adapters, mutable domain entities, and any class that holds state and is not designed for extension gets `@final`. This communicates "use this, don't subclass it."

### @override

4. **Mark every method that implements a Protocol or overrides a parent.** Every method on an adapter that satisfies a port gets `@override`. Every method on a framework subclass that overrides a base gets `@override`. No exceptions.

5. **`@override` is a signal, not just a check.** It tells the reader "this method exists because of a contract" without having to trace the class hierarchy. The type checker verifying the parent method exists is a bonus.

### Unused Returns

6. **Assign unused return values to `_`.** When a function returns a value the caller doesn't need, assign it to `_` rather than silently discarding it. This makes the discard intentional and visible.

```python
_ = get_build_status.execute("job/deploy", "10")
instances, _ = config_loader.load()
```

## Examples

### Mypy configuration

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_untyped_calls = false
```

### Use case — @final, fully annotated

```python
@final
class TriggerBuild:
    def __init__(self, client: JenkinsClient) -> None:
        self._client = client

    def execute(self, job_path: str, parameters: dict[str, str] | None = None) -> str:
        return self._client.trigger_build(job_path, parameters)
```

### Adapter — @final class, @override methods

```python
@final
class RestClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._session = requests.Session()
        self._base_url = base_url
        self._session.headers["Authorization"] = f"Bearer {token}"

    @override
    def list_items(self) -> list[Item]:
        resp = self._session.get(f"{self._base_url}/api/items")
        resp.raise_for_status()
        return [Item(**entry) for entry in resp.json()["items"]]

    @override
    def get_status(self, item_id: str) -> ItemStatus:
        resp = self._session.get(f"{self._base_url}/api/items/{item_id}")
        resp.raise_for_status()
        return ItemStatus(**resp.json())
```
