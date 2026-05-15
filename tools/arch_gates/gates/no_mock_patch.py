"""Gate: tests must not use unittest.mock.patch decorators."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Violation

NAME = "no-mock-patch"
DESCRIPTION = "Tests must use monkeypatch, not unittest.mock.patch decorators."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        # Only check test files
        if "/tests/" not in str(mod.path):
            continue
        for node in ast.walk(mod.tree):
            # Check for @patch or @mock.patch decorators
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if _is_patch_decorator(dec):
                        violations.append(
                            Violation(
                                file=str(mod.path),
                                line=dec.lineno,
                                message=f"Use monkeypatch instead of @patch on '{node.name}'",
                            )
                        )
            # Check for `with patch(...)` context managers
            if isinstance(node, ast.With):
                for item in node.items:
                    if _is_patch_call(item.context_expr):
                        violations.append(
                            Violation(
                                file=str(mod.path),
                                line=node.lineno,
                                message="Use monkeypatch instead of 'with patch(...)'",
                            )
                        )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _is_patch_decorator(node: ast.expr) -> bool:
    """Check if a decorator is @patch or @mock.patch."""
    # @patch(...)
    if isinstance(node, ast.Call):
        return _is_patch_name(node.func)
    # @patch (without call — unlikely but possible)
    return _is_patch_name(node)


def _is_patch_name(node: ast.expr) -> bool:
    """Check if a node refers to 'patch' or 'mock.patch'."""
    if isinstance(node, ast.Name) and node.id == "patch":
        return True
    return isinstance(node, ast.Attribute) and node.attr == "patch"


def _is_patch_call(node: ast.expr) -> bool:
    """Check if an expression is a patch(...) call."""
    if isinstance(node, ast.Call):
        return _is_patch_name(node.func)
    return False
