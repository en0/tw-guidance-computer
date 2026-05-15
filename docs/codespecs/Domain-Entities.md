---
name: domain-entities
description: Domain entities with identity, lifecycle, and business behavior. Immutability preferred. Use when writing or reviewing domain models with state transitions or business rules.
---

# Domain Entities

## Decision

Domain entities are dataclasses with identity, lifecycle, and business behavior. They own the logic that governs their state — transitions, validations, and business rules live on the entity, not in use cases. Immutability (`frozen=True`) is preferred but not required. When mutable, entities must be marked `@final` to protect internal state.

## Why It Matters

When business logic lives in use cases instead of on the objects that own the state, the rules get scattered. Two use cases that both transition a todo item's status will each implement their own validation — and eventually diverge. The entity is the single authority for what its state can do and how it changes.

Entities differ from value objects in what they carry. Value objects are pure data with self-validation and derived properties. Entities have behavior — methods that enforce business rules, govern state transitions, and make decisions. Both live in the domain layer. Both validate invariants at construction. The distinction is whether the object has logic beyond describing itself.

## Rules

1. **Prefer `@dataclass(frozen=True)`.** Immutable entities return new instances from behavior methods. This eliminates shared-mutable-state bugs and makes entities safe to pass between layers. Use mutable entities only when the frozen pattern becomes impractical (e.g., many fields changing frequently, performance-critical paths).

2. **Mutable entities must be `@final`.** If the entity is not frozen, mark it `@final` to prevent subclassing that could break internal state assumptions.

3. **Validate in `__post_init__`.** Same as value objects — enforce invariants at construction. An entity in an invalid state must never exist.

4. **Business logic lives on the entity.** State transitions, validation of transitions, and business rules are methods on the entity. Use cases call these methods — they don't reimplement the logic.

5. **Behavior methods on frozen entities return new instances.** A `transition()` method returns a new entity with the updated state. The caller replaces its reference.

6. **Behavior methods on mutable entities modify in place.** A `transition()` method updates internal state directly. Mark these methods clearly.

7. **Entities live in `domain/models.py` alongside value objects.** Same location rules — one file by default, `domain/models/` sub-module with one file per model when the count grows. Re-export from `__init__.py`. See **Hexagonal-Architecture.md** for the directory layout.

8. **Factory fixtures for testing.** Same pattern as value objects — factory fixtures with sane defaults. See **Fixture-Centralized-Construction.md**.

## Examples

### Frozen entity with state transitions (preferred)

```python
@dataclass(frozen=True)
class TodoItem:
    id: str
    title: str
    status: TodoStatus = TodoStatus.TODO

    _valid_transitions: ClassVar[dict[TodoStatus, set[TodoStatus]]] = {
        TodoStatus.TODO: {TodoStatus.DOING},
        TodoStatus.DOING: {TodoStatus.DONE, TodoStatus.TODO},
        TodoStatus.DONE: set(),
    }

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise TodoValidationError("Title must not be empty")

    def transition(self, new_status: TodoStatus) -> TodoItem:
        if new_status not in self._valid_transitions.get(self.status, set()):
            raise InvalidTransitionError(
                f"Cannot transition from {self.status.value} to {new_status.value}"
            )
        return replace(self, status=new_status)

    @property
    def valid_transitions(self) -> set[TodoStatus]:
        return self._valid_transitions.get(self.status, set())
```

### Mutable entity (when frozen is impractical)

```python
@final
@dataclass
class Session:
    id: str
    user_id: str
    state: SessionState = SessionState.ACTIVE
    last_activity: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise SessionError("User ID must not be empty")

    def touch(self) -> None:
        if self.state != SessionState.ACTIVE:
            raise SessionError("Cannot touch an inactive session")
        self.last_activity = datetime.now()

    def expire(self) -> None:
        if self.state != SessionState.ACTIVE:
            raise SessionError("Session is already inactive")
        self.state = SessionState.EXPIRED
```

### Use case calling entity behavior

```python
@final
class TransitionTodo:
    def __init__(self, store: TodoStore) -> None:
        self._store = store

    def execute(self, todo_id: str, new_status: TodoStatus) -> TodoItem:
        item = self._store.get(todo_id)
        updated = item.transition(new_status)  # entity owns the logic
        self._store.save(updated)
        return updated
```

The use case doesn't check valid transitions — the entity does. The use case orchestrates; the entity decides.

### Factory fixture

```python
@pytest.fixture()
def make_todo_item():
    def _factory(**kwargs):
        kwargs.setdefault("id", "todo-1")
        kwargs.setdefault("title", "Write tests")
        kwargs.setdefault("status", TodoStatus.TODO)
        return TodoItem(**kwargs)
    return _factory
```

### Testing state transitions

```python
class TestTodoItem:
    def test_transition_todo_to_doing(self, make_todo_item):
        item = make_todo_item()
        result = item.transition(TodoStatus.DOING)
        assert result.status == TodoStatus.DOING

    def test_transition_done_raises(self, make_todo_item):
        item = make_todo_item(status=TodoStatus.DONE)
        with pytest.raises(InvalidTransitionError):
            item.transition(TodoStatus.TODO)

    def test_valid_transitions_from_doing(self, make_todo_item):
        item = make_todo_item(status=TodoStatus.DOING)
        assert item.valid_transitions == {TodoStatus.DONE, TodoStatus.TODO}
```

## Entity vs Value Object

| | Value Object | Entity |
|---|---|---|
| Identity | By value (all fields) | By ID field |
| Behavior | Derived properties only | State transitions, business rules |
| Immutability | Always frozen | Preferred frozen, mutable when justified |
| `@final` | Never | Required when mutable |
| Lifecycle | None — constructed and used | Has state that changes over time |
| Example | `SearchQuery`, `Money`, `EmailAddress` | `TodoItem`, `Session`, `Order` |
