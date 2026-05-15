"""Gate: domain and application may only raise and catch DomainError subclasses."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "domain-exceptions-only"
DESCRIPTION = "Domain and application may only raise and catch exceptions imported from domain.exceptions."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer not in (Layer.DOMAIN, Layer.APPLICATION):
            continue
        # Build a set of exception names that were imported from domain.exceptions
        # in this module. Any raise or except of a name not in this set is a violation.
        domain_exceptions = _collect_domain_exception_names(mod.tree)
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.Raise) and node.exc is not None:
                name = _exception_name(node.exc)
                if name and name not in domain_exceptions:
                    violations.append(
                        Violation(
                            file=str(mod.path),
                            line=node.lineno,
                            message=f"Raises non-domain exception: {name}",
                        )
                    )
            # Check except handlers for non-domain exceptions
            if isinstance(node, ast.ExceptHandler) and node.type is not None:
                name = _handler_exception_name(node.type)
                if name and name not in domain_exceptions:
                    violations.append(
                        Violation(
                            file=str(mod.path),
                            line=node.lineno,
                            message=f"Catches non-domain exception: {name}",
                        )
                    )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _exception_name(node: ast.expr) -> str | None:
    """Extract the exception class name from a raise statement.

    Handles three forms:
      - raise SomeError              -> ast.Name
      - raise SomeError("msg")       -> ast.Call with ast.Name func
      - raise module.SomeError("msg") -> ast.Call with ast.Attribute func
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _handler_exception_name(node: ast.expr) -> str | None:
    """Extract the exception class name from an except handler.

    Handles:
      - except SomeError:            -> ast.Name
      - except module.SomeError:     -> ast.Attribute
    Tuple forms (except (A, B):) are not checked — each element would need
    individual validation which we can add later if needed.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect_domain_exception_names(tree: ast.Module) -> set[str]:
    """Collect names imported from domain.exceptions in this module.

    Handles aliased imports: `from domain.exceptions import InvalidName as BadName`
    would add "BadName" to the set since that's the name used in raise/except statements.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "domain.exceptions" in node.module:
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names
