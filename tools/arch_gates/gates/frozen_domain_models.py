"""Gate: all dataclasses in domain/ must be frozen."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "frozen-domain-models"
DESCRIPTION = "All dataclasses in domain/ must use frozen=True."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.DOMAIN:
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            dc_decorator = _find_dataclass_decorator(node)
            if dc_decorator is None:
                continue
            if not _has_frozen_true(dc_decorator):
                violations.append(
                    Violation(
                        file=str(mod.path),
                        line=node.lineno,
                        message=f"Domain dataclass '{node.name}' is not frozen",
                    )
                )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _find_dataclass_decorator(node: ast.ClassDef) -> ast.expr | None:
    for d in node.decorator_list:
        if isinstance(d, ast.Name) and d.id == "dataclass":
            return d
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass":
            return d
        if isinstance(d, ast.Attribute) and d.attr == "dataclass":
            return d
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "dataclass":
            return d
    return None


def _has_frozen_true(decorator: ast.expr) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    for kw in decorator.keywords:
        if kw.arg == "frozen" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False
