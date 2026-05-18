"""Gate: every public method in inbound adapters must handle the base domain exception."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "inbound-exception-boundary"
DESCRIPTION = "Every public method in adapters/inbound/ must handle the base domain exception."

_SKIP_METHODS = {"__init__", "__post_init__"}


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.ADAPTERS:
            continue
        if "inbound" not in mod.path.parts:
            continue
        if mod.path.name == "__init__.py":
            continue

        # Collect domain exception names imported in this module
        domain_exceptions = _collect_domain_exception_names(mod.tree)

        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if item.name.startswith("_") or item.name in _SKIP_METHODS:
                    continue
                if not _has_exception_boundary(item, domain_exceptions):
                    violations.append(
                        Violation(
                            file=str(mod.path),
                            line=item.lineno,
                            message=f"Public method '{node.name}.{item.name}' has no exception boundary",
                        )
                    )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _has_exception_boundary(func: ast.FunctionDef, domain_exceptions: set[str]) -> bool:
    """Check if the function handles domain exceptions via except or with statement."""
    for node in ast.walk(func):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            name = _handler_name(node.type)
            if name and name in domain_exceptions:
                return True
        if isinstance(node, ast.With):
            return True
    return False


def _handler_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect_domain_exception_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "domain.exceptions" in node.module:
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names
