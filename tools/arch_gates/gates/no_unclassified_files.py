"""Gate: no unrecognized files outside the defined layers."""

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "no-unclassified-files"
DESCRIPTION = "All Python files must belong to a recognized architectural layer."


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer == Layer.OTHER:
            violations.append(
                Violation(
                    file=str(mod.path),
                    line=1,
                    message="File does not belong to any recognized layer",
                )
            )
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)
