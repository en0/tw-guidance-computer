"""Gate: lint suppression comments only allowed in adapters/ and root-level modules."""

from tools.arch_gates.models import GateContext, GateResult, Layer, Violation

NAME = "lint-suppressions"
DESCRIPTION = (
    "Lint suppression comments (type: ignore, noqa, pragma: no cover) "
    "are only permitted in adapters/ and root-level modules."
)

SUPPRESSION_PATTERNS = [
    "type: ignore",
    "# noqa",
    "# pragma: no cover",
]


def check(ctx: GateContext) -> GateResult:
    violations = []
    for mod in ctx.modules:
        if mod.layer in (Layer.ADAPTERS, Layer.ROOT):
            continue
        for i, line in enumerate(mod.source.splitlines(), 1):
            for pattern in SUPPRESSION_PATTERNS:
                if pattern in line:
                    violations.append(
                        Violation(
                            file=str(mod.path),
                            line=i,
                            message=f"'{pattern}' not allowed outside adapters and root",
                        )
                    )
                    break  # one violation per line, even if multiple patterns match
    return GateResult(name=NAME, description=DESCRIPTION, passed=not violations, violations=violations)
