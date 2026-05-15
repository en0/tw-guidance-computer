"""Gate: adapter classes implementing ports must use @override on every method."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "override-on-port-impls"
DESCRIPTION = "Adapter methods implementing a port must be decorated with @override."


def check(ctx: GateContext) -> GateResult:
    # Step 1: collect all port class names and their method names
    port_methods = _collect_port_methods(ctx)
    if not port_methods:
        return GateResult(name=NAME, description=DESCRIPTION, passed=True, violations=[])

    # Step 2: find adapter classes that inherit from a port and check for @override
    violations = []
    for mod in ctx.modules:
        if mod.layer != Layer.ADAPTERS:
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # Check if this class inherits from any known port
            inherited_ports = _get_inherited_ports(node, port_methods)
            if not inherited_ports:
                continue
            # Collect methods that should have @override
            required_methods: set[str] = set()
            for port_name in inherited_ports:
                required_methods.update(port_methods[port_name])
            # Check each method in the class
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name.startswith("_"):
                    continue
                if item.name not in required_methods:
                    continue
                has_override = any(
                    (isinstance(d, ast.Name) and d.id == "override")
                    or (isinstance(d, ast.Attribute) and d.attr == "override")
                    for d in item.decorator_list
                )
                if not has_override:
                    violations.append(
                        Violation(
                            file=str(mod.path),
                            line=item.lineno,
                            message=f"Method '{item.name}' on '{node.name}' implements a port but missing @override",
                        )
                    )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _collect_port_methods(ctx: GateContext) -> dict[str, set[str]]:
    """Collect port class names and their public method names from application/ports/."""
    ports: dict[str, set[str]] = {}
    for mod in ctx.modules:
        if mod.layer != Layer.APPLICATION:
            continue
        if "ports" not in mod.path.parts:
            continue
        for node in ast.walk(mod.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods: set[str] = set()
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    methods.add(item.name)
            if methods:
                ports[node.name] = methods
    return ports


def _get_inherited_ports(node: ast.ClassDef, port_methods: dict[str, set[str]]) -> list[str]:
    """Return list of port names this class inherits from."""
    inherited = []
    for base in node.bases:
        name = None
        if isinstance(base, ast.Name):
            name = base.id
        elif isinstance(base, ast.Attribute):
            name = base.attr
        if name and name in port_methods:
            inherited.append(name)
    return inherited
