"""Gate: enforce layer import boundaries for all architectural layers."""

import ast

from tools.arch_gates.models import GateContext, GateResult, Layer, ParsedModule, Violation
from tools.arch_gates.parser import classify_import, extract_import_module

NAME = "layer-imports"
DESCRIPTION = "Each layer may only import from its allowed set of layers."

# Define what each layer is allowed to import from.
# Layers not listed here are unconstrained (e.g., adapters, root).
LAYER_RULES: dict[Layer, set[Layer]] = {
    Layer.DOMAIN: {Layer.DOMAIN, Layer.STDLIB},
    Layer.APPLICATION: {Layer.APPLICATION, Layer.DOMAIN, Layer.STDLIB},
    Layer.ADAPTERS: {Layer.ADAPTERS, Layer.APPLICATION, Layer.DOMAIN, Layer.ROOT, Layer.STDLIB, Layer.EXTERNAL},
}


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        allowed = LAYER_RULES.get(mod.layer)
        if allowed is None:
            continue
        _check_module(mod, allowed, ctx.layer_map, violations)
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)


def _check_module(
    mod: ParsedModule,
    allowed: set[Layer],
    layer_map: dict[str, Layer],
    violations: list[Violation],
) -> None:
    for node in ast.walk(mod.tree):
        module_name = extract_import_module(node)
        if module_name is None:
            continue
        layer = classify_import(module_name, layer_map)
        if layer not in allowed:
            violations.append(
                Violation(
                    file=str(mod.path),
                    line=node.lineno,
                    message=f"{mod.layer.value} imports '{module_name}' (layer: {layer.value})",
                )
            )
