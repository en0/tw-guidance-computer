"""Gate: every except block in outbound adapters must translate to a domain exception or return."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "outbound-exception-translation"
DESCRIPTION = "Every except block in adapters/outbound/ must raise a domain exception (from e) or return a safe value."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.ADAPTERS:
            continue
        if "outbound" not in mod.path.parts:
            continue
        if mod.path.name == "__init__.py":
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if _has_raise_from(node) or _has_return(node):
                continue
            violations.append(
                Violation(
                    file=str(mod.path),
                    line=node.lineno,
                    message="except block does not raise a domain exception (from e) or return",
                )
            )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _has_raise_from(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise) and node.cause is not None:
            return True
    return False


def _has_return(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if isinstance(node, ast.Return):
            return True
    return False
