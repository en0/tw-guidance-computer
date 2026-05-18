"""Utilities for parsing and classifying Python modules."""

import ast
import sys
from pathlib import Path

from tools.arch_gates.models import GateContext, Layer, ParsedModule

SOURCE_LAYER_DIRS = {d.value: d for d in Layer if d in (Layer.DOMAIN, Layer.APPLICATION, Layer.ADAPTERS)}
ROOT_FILES = {"compose.py", "hud.py", "cli.py", "__main__.py", "__init__.py"}

# Package prefix to strip from absolute imports before layer classification.
# Set this to the top-level package name used in import statements.
PACKAGE_PREFIX = "tw_guidance_computer"


def classify_layer(path: Path, root: Path) -> Layer:
    """Classify a file's architectural layer based on its path relative to root."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return Layer.OTHER

    parts = rel.parts
    if not parts:
        return Layer.OTHER

    if len(parts) == 1 and rel.name in ROOT_FILES:
        return Layer.ROOT

    first_dir = parts[0]
    if first_dir in SOURCE_LAYER_DIRS:
        return SOURCE_LAYER_DIRS[first_dir]

    return Layer.OTHER


def path_to_module_name(path: Path, root: Path) -> str:
    """Convert a file path to a dotted module name relative to root."""
    rel = path.relative_to(root)
    parts = rel.with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def classify_import(module_name: str, layer_map: dict[str, Layer]) -> Layer:
    """Classify an imported module name by checking the layer map, stdlib, then external."""
    # Strip package prefix for absolute imports
    stripped = module_name
    if PACKAGE_PREFIX and module_name.startswith(PACKAGE_PREFIX + "."):
        stripped = module_name[len(PACKAGE_PREFIX) + 1 :]

    if stripped in layer_map:
        return layer_map[stripped]
    for known, layer in layer_map.items():
        if stripped.startswith(known + "."):
            return layer

    # Also check unstripped (for cases where prefix doesn't apply)
    if module_name in layer_map:
        return layer_map[module_name]
    for known, layer in layer_map.items():
        if module_name.startswith(known + "."):
            return layer

    top_level = module_name.split(".")[0]
    if top_level in sys.stdlib_module_names:
        return Layer.STDLIB
    return Layer.EXTERNAL


def build_layer_map(modules: list[ParsedModule]) -> dict[str, Layer]:
    """Build a mapping of module names to their layers."""
    layer_map: dict[str, Layer] = {}
    for mod in modules:
        layer_map[mod.module_name] = mod.layer
    return layer_map


def extract_import_module(node: ast.AST) -> str | None:
    """Extract the module name from an import or from-import node."""
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else None
    if isinstance(node, ast.ImportFrom):
        if node.module:
            return node.module
        if node.names:
            return node.names[0].name
    return None


def parse_codebase(root: Path) -> GateContext:
    """Walk a source directory and return a fully classified gate context."""
    modules = []
    for path in sorted(root.rglob("*.py")):
        source = path.read_text()
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        layer = classify_layer(path, root)
        module_name = path_to_module_name(path, root)
        modules.append(ParsedModule(path=path, layer=layer, tree=tree, source=source, module_name=module_name))

    layer_map = build_layer_map(modules)
    return GateContext(modules=modules, layer_map=layer_map)
