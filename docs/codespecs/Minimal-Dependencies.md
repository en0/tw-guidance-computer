# Minimal Dependencies

## Decision

Every dependency is a deliberate choice. Projects depend on small, focused packages that do one thing. Fat frameworks that pull in large transitive dependency trees are avoided. If the standard library can do the job, use it.

## Why It Matters

Every dependency is code you don't control. It can break, change its API, introduce vulnerabilities, or pull in transitive dependencies that conflict with something else. The cost of a dependency isn't just the import — it's the maintenance burden of tracking updates, auditing changes, and dealing with breakage across your entire dependency tree.

Small projects with few dependencies are easy to audit, easy to update, and easy to understand. When something breaks, the surface area you need to investigate is small.

## Rules

1. **Prefer the standard library.** `dataclasses`, `pathlib`, `json`, `typing`, `enum`, `logging` — Python's standard library covers most infrastructure needs. Don't add a dependency for something the stdlib already does.

2. **Each dependency must do one thing you can't reasonably do yourself.** `requests` for HTTP. `pyyaml` for YAML parsing. `pygame` for a game loop. If you can't articulate the specific capability a package provides, you don't need it.

3. **No fat frameworks for small projects.** If a package pulls in dozens of transitive dependencies to give you one feature, find a smaller alternative or write the feature yourself. The dependency cost must be proportional to the value.

4. **Use official or canonical packages.** For API clients, prefer the vendor's official SDK or a well-maintained community standard. Don't pull in a wrapper-of-a-wrapper when the underlying library is already simple.

5. **Understand what you import.** Before adding a dependency, read enough of its source to know what it does, what it depends on, and how it behaves on failure. If you can't explain what a package does without reading its README, you don't understand it well enough to depend on it.

6. **Pin build tools, not runtime dependencies.** `uv.lock` handles reproducible installs. `pyproject.toml` declares compatible ranges for runtime dependencies (`>=3.12`, `>=0.7,<0.8` for build tools). Don't over-constrain ranges that will cause resolution conflicts downstream.

7. **Type stubs go in dev dependencies.** Packages like `types-requests` and `types-pyyaml` are development tools, not runtime requirements. They belong in `[dependency-groups] dev`.
