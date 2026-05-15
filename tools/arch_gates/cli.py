"""CLI entry point for architecture gates."""

import importlib
import pkgutil
import sys
from collections.abc import Callable
from pathlib import Path

from tools.arch_gates import gates as gates_package
from tools.arch_gates.models import GateContext, GateResult
from tools.arch_gates.parser import parse_codebase


def discover_gates() -> list[tuple[str, str, Callable[[GateContext], GateResult]]]:
    """Discover all gate modules in the gates package."""
    result = []
    for info in pkgutil.iter_modules(gates_package.__path__):
        module = importlib.import_module(f"tools.arch_gates.gates.{info.name}")
        check = getattr(module, "check", None)
        name = getattr(module, "NAME", None)
        description = getattr(module, "DESCRIPTION", None)

        if not check:
            print(f"WARNING: gates/{info.name}.py has no check() function, skipping", file=sys.stderr)
            continue
        if not name:
            print(f"WARNING: gates/{info.name}.py is missing NAME, skipping", file=sys.stderr)
            continue
        if not description:
            print(f"WARNING: gates/{info.name}.py is missing DESCRIPTION, skipping", file=sys.stderr)
            continue

        result.append((name, description, check))
    return result


def run(src_path: Path, gate_filter: list[str] | None = None) -> int:
    """Parse modules, run gates, print results, return exit code."""
    ctx = parse_codebase(src_path)
    discovered = discover_gates()

    if gate_filter:
        discovered = [(n, d, c) for n, d, c in discovered if n in gate_filter]
        unknown = set(gate_filter) - {n for n, _, _ in discovered}
        if unknown:
            print(f"Unknown gate(s): {', '.join(sorted(unknown))}")
            return 1

    results: list[GateResult] = []
    for _, _, check in discovered:
        result = check(ctx)
        results.append(result)

    failed = False
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.description}")
        if not result.passed:
            failed = True
            for v in result.violations:
                print(f"  {v.file}:{v.line}: {v.message}")

    if failed:
        print(f"\n{sum(1 for r in results if not r.passed)}/{len(results)} gates failed.")
        return 1

    print(f"\nAll {len(results)} gates passed.")
    return 0


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Architecture gate checker")
    parser.add_argument("src_path", type=Path, help="Path to source directory")
    parser.add_argument("--gate", type=str, nargs="+", default=None, help="Run specific gate(s) by name")
    args = parser.parse_args()

    sys.exit(run(args.src_path, args.gate))
