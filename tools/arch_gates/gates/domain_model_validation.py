"""Gate: all frozen dataclasses in domain/ must have __post_init__ validation."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "domain-model-validation"
DESCRIPTION = "All frozen dataclasses in domain/ must define __post_init__."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.DOMAIN:
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not _is_frozen_dataclass(node):
                continue
            if node.name.startswith("_"):
                continue
            if not _has_post_init(node):
                violations.append(
                    Violation(
                        file=str(mod.path),
                        line=node.lineno,
                        message=f"Frozen dataclass '{node.name}' is missing __post_init__",
                    )
                )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _is_frozen_dataclass(node: ast.ClassDef) -> bool:
    for d in node.decorator_list:
        if isinstance(d, ast.Call):
            func = d.func
            if isinstance(func, ast.Name) and func.id == "dataclass":
                return _has_frozen_kwarg(d)
            if isinstance(func, ast.Attribute) and func.attr == "dataclass":
                return _has_frozen_kwarg(d)
    return False


def _has_frozen_kwarg(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "frozen" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def _has_post_init(node: ast.ClassDef) -> bool:
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__post_init__":
            return True
    return False
