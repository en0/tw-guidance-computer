# Composition Root

## Decision

Every application has a single composition root — the one place that knows about all layers, wires dependencies together, and starts the program. Construction logic is isolated here and nowhere else. The simplest wiring mechanism that meets the complexity demands is used: manual constructor injection for closed applications, a DI container when the system requires a pluggable model.

## Why It Matters

If construction is scattered — a use case instantiating its own adapter, an adapter building its own config — the dependency graph becomes invisible. You can't see what depends on what without reading every file. Testing gets harder because you can't swap implementations without patching internals. Changes to a constructor signature ripple unpredictably.

A single composition root makes the entire dependency graph visible in one place. Every object gets its dependencies handed to it. Nothing constructs its own collaborators. When something changes, there's exactly one place to update the wiring.

This is the application-level equivalent of what fixture-centralized construction does for tests — one place builds things, everything else just uses what it's given.

## Rules

1. **One composition root per project.** A single module centralizes all construction logic. Entry points (CLI, HUD, server) are thin shells that configure and invoke the root — they don't construct use cases or adapters themselves.

2. **Entry points are thin shells.** `cli.py`, `hud.py`, `server.py` — each parses its own input (CLI args, config files) and passes configuration to the composition root. They don't construct use cases or adapters directly.

3. **Constructor injection is the wiring mechanism.** Dependencies are passed as constructor arguments. No service locators, no global registries, no module-level singletons. Nothing outside the composition root constructs a use case or adapter — if code needs a collaborator, it receives one through its constructor.

4. **Dynamic binding is fine — it still happens in the root.** If the application needs to select implementations based on CLI flags, environment variables, or config files, that decision logic lives in the composition root. The rest of the code doesn't know or care which implementation was chosen.

5. **Use a DI container when the complexity demands it.** Legitimate cases include:
   - **The composition root can't be fully known at design time.** Frameworks and extensible systems where consumers inject their own services or override defaults.
   - **The composition graph is very large.** Autowire-style containers make adding new components trivial — create the class, decorate it, add it to constructors where needed. On a 10-year-old project with hundreds of classes, this matters.
   - **Composition changes at runtime.** Feature toggles, account-level toggles, SaaS systems where the wiring depends on who's using it. This kind of conditional construction gets complex fast; a container can absorb that complexity.

   The container replaces manual wiring but the principle is the same — construction is isolated, not scattered. Boundary rules still apply.

6. **Typed containers for grouping related dependencies.** When multiple use cases or services need to be passed around together (e.g., per-instance in a multi-tenant system), use a frozen dataclass as a typed container. This is not a service locator — it's a struct with named, typed fields constructed in the root.

## Examples

### Manual wiring — closed application

```python
def main() -> None:
    config = ConfigLoader().load()
    client = RestClient(config.base_url)
    cache = FileCache(build_cache_dir())

    use_cases = UseCaseContainer(
        list_items=ListItems(client),
        get_status=GetStatus(client),
        search=Search(cache),
    )

    server = FastMCP("my-server")
    register_tools(server, use_cases)
    server.run()
```

### Manual wiring — CLI tool

```python
def main(args: list[str]) -> None:
    parsed = parse_args(args)
    client = ApiClient(base_url=parsed.url, token=parsed.token)
    use_case = ProcessData(client)
    result = use_case.execute(parsed.input_file)
    print(result)
```

### DI container — framework with pluggable services

When consumers need to override or extend services, a container earns its keep.

```python
class GameEngine:
    def __init__(
        self,
        *,
        service_scan_path: list[str] | None = None,
        services: dict[type, type] | None = None,
    ):
        modules = ["my_engine.service"]
        if service_scan_path:
            modules.extend(service_scan_path)
        builder = AutoWireContainerBuilder(modules)
        for annotation, impl in (services or {}).items():
            builder.bind(annotation, impl, "SINGLETON")
        self._container = builder.build()
```

The container is still constructed in one place. The consumer influences *what* gets wired, but the *where* is fixed.

### Typed container — grouping related dependencies

```python
@dataclass(frozen=True)
class InstanceContainer:
    instance: SomeConfig
    list_items: ListItems
    get_status: GetStatus
    trigger_action: TriggerAction
```

Constructed in the root, passed as a unit. Not a service locator — it's a frozen struct with no resolution logic.

## When Construction Outside the Root Is Acceptable

- **Value objects.** Creating a `SearchQuery(term="foo", limit=10)` in a use case is fine — that's data, not a collaborator.
- **Adapter-internal helpers.** An adapter creating a `requests.Session` in its own `__init__` is fine — that's an implementation detail of the adapter, not a dependency the application cares about.

## Testing Implications

The wiring mechanism changes how you set up tests, but the principle doesn't.

- **Manual wiring:** Test fixtures construct the unit under test directly, injecting mocks or fakes for ports. Monkeypatch swaps adapter internals when needed.
- **DI container:** Test fixtures build the real container and override only the boundary implementations with fakes. The container wires everything else for real. Services under test are fully wired objects, not mocks.

In both cases, you swap at the boundary and test real behavior. The tooling differs — `monkeypatch.setattr` vs `builder.bind(IPort, FakeImpl)` — but the isolation point is the same.
