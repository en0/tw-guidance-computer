"""Architecture gate models."""

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Layer(Enum):
    """Architectural layer classification."""

    DOMAIN = "domain"
    APPLICATION = "application"
    ADAPTERS = "adapters"
    ROOT = "root"
    STDLIB = "stdlib"
    EXTERNAL = "external"
    OTHER = "other"


@dataclass(frozen=True)
class Violation:
    """A single rule violation."""

    file: str
    line: int
    message: str


@dataclass(frozen=True)
class GateResult:
    """Result of running a single gate."""

    name: str
    description: str
    passed: bool
    violations: list[Violation] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedModule:
    """A parsed Python module with layer classification."""

    path: Path
    layer: Layer
    tree: ast.Module
    source: str
    module_name: str


@dataclass(frozen=True)
class GateContext:
    """Pre-parsed codebase data passed to every gate."""

    modules: list[ParsedModule]
    layer_map: dict[str, Layer]
