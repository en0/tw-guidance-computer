"""Gate: all use case classes in application/ must be decorated with @final."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "final-use-cases"
DESCRIPTION = "All use case classes in application/ (excluding ports/) must be @final."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.APPLICATION:
            continue
        if "ports" in mod.path.parts or mod.path.name == "__init__.py":
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            has_final = any(
                (isinstance(d, ast.Name) and d.id == "final")
                or (isinstance(d, ast.Attribute) and d.attr == "final")
                for d in node.decorator_list
            )
            if not has_final:
                violations.append(
                    Violation(
                        file=str(mod.path),
                        line=node.lineno,
                        message=f"Use case '{node.name}' is missing @final",
                    )
                )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)
