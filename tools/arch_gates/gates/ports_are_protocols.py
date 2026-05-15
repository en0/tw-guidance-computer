"""Gate: port definitions must be typing.Protocol classes."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "ports-are-protocols"
DESCRIPTION = "All classes in application/ports/ must inherit from typing.Protocol."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.APPLICATION:
            continue
        if "ports" not in mod.path.parts or mod.path.name == "__init__.py":
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # Check if any base class is Protocol
            # Handles: Protocol, typing.Protocol
            has_protocol = any(
                (isinstance(b, ast.Name) and b.id == "Protocol")
                or (isinstance(b, ast.Attribute) and b.attr == "Protocol")
                for b in node.bases
            )
            if not has_protocol:
                violations.append(
                    Violation(
                        file=str(mod.path),
                        line=node.lineno,
                        message=f"Port class '{node.name}' does not inherit from Protocol",
                    )
                )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)
