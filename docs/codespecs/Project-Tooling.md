# Project Tooling

## Decision

Every project uses uv for package management and builds, a `src/` layout for source code, and pre-commit hooks that run ruff, mypy, and pytest before every commit. Python 3.12 minimum. All tool configuration lives in `pyproject.toml`.

## Why It Matters

Tooling decisions made once at project creation affect every subsequent interaction with the codebase. A consistent setup means no time spent choosing tools, configuring them, or debugging tool conflicts. Pre-commit hooks mean broken code never reaches the repository — linting, type checking, and tests all run before the commit is accepted.

The `src/` layout prevents a common class of import bugs where tests accidentally import from the working directory instead of the installed package. uv replaces pip, virtualenv, and build tooling with a single fast tool. `pyproject.toml` replaces `setup.cfg`, `setup.py`, `mypy.ini`, `pytest.ini`, and `.flake8` with one file.

## Rules

### Package Management

1. **uv for everything.** Dependency resolution, virtual environments, builds, and script running. No pip, no poetry, no setuptools.

2. **uv-build as the build backend.** Replaces setuptools and hatchling. Configured in `[build-system]`.

3. **Dev dependencies in a dependency group, not extras.** `[dependency-groups] dev = [...]` keeps dev tools out of the package metadata.

### Project Layout

4. **`src/` layout.** Source code lives under `src/<package_name>/`. Tests live under `tests/` at the project root, mirroring the source structure.

5. **Single `pyproject.toml` for all configuration.** Ruff, mypy, pytest markers, build system — everything in one file. No `setup.cfg`, no `mypy.ini`, no `pytest.ini`.

### Pre-commit Hooks

6. **Pre-commit runs on every commit.** No exceptions. If the hooks fail, the commit is rejected.

7. **Hook chain: whitespace cleanup → formatting → linting → type checking → tests.** In that order. Fast checks first, slow checks last.

8. **Ruff replaces flake8, isort, and pyupgrade.** One tool for linting and import sorting. Configured with `--fix` to auto-correct what it can.

9. **Mypy runs with the same strict config as CI.** The pre-commit mypy hook includes `additional_dependencies` for type stubs so it matches the project's type checking exactly.

10. **Pytest runs as a local hook.** Uses the project's `.venv/bin/pytest` directly, `always_run: true`, `pass_filenames: false`. Every commit runs the full test suite.

### Ruff Configuration

11. **Minimum rule set: `E`, `F`, `I`, `D`, `UP`, `B`.** Pycodestyle errors, pyflakes, isort, pydocstyle, pyupgrade, and flake8-bugbear. This catches real problems without drowning in style noise.

12. **Docstring rules disabled for tests.** `"tests/**" = ["D"]` in per-file-ignores. Tests don't need docstrings — the test name is the documentation.

13. **Google docstring convention.** Configured via `[tool.ruff.lint.pydocstyle] convention = "google"`.

## Examples

### pyproject.toml

```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "requests",
]

[project.scripts]
my-project = "my_project.__main__:cli"

[build-system]
requires = ["uv-build>=0.7,<0.8"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "my_project"

[dependency-groups]
dev = [
    "pre-commit",
    "pytest",
    "mypy",
    "types-requests",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "D", "UP", "B"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.pytest.ini_options]
markers = [
    "mock_response: pre-configure mock response on patched_client fixture",
]

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

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: .venv/bin/pytest
        language: system
        pass_filenames: false
        always_run: true
        stages: [pre-commit]
```

### Directory layout

```
my-project/
├── pyproject.toml
├── uv.lock
├── .pre-commit-config.yaml
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── __main__.py
│       ├── domain/
│       ├── application/
│       └── adapters/
└── tests/
    ├── conftest.py
    ├── test_domain/
    ├── test_application/
    └── test_adapters/
```
