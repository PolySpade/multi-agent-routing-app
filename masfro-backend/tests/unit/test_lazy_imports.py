"""
AST-based validation that heavy modules are imported lazily.

The low-RAM branch moved osmnx, rasterio, numpy, pandas, and selenium
imports into function bodies so they are only loaded when actually needed.
This test parses each source file's AST and fails if any of those modules
appear as a top-level (module-scope) import.
"""

import ast
import os
from pathlib import Path

import pytest

# Root of the backend package
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
APP_ROOT = BACKEND_ROOT / "app"


def _get_module_level_imports(filepath: Path) -> list[tuple[str, int]]:
    """
    Parse a Python file and return heavy imports that are at module level.

    Returns a list of (module_name, line_number) tuples for imports that
    appear outside any function/method body.
    """
    HEAVY_MODULES = {"osmnx", "rasterio", "numpy", "pandas", "selenium"}

    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))

    violations = []

    # Only check top-level statements (not nested inside FunctionDef/AsyncFunctionDef)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_module = alias.name.split(".")[0]
                if top_module in HEAVY_MODULES:
                    violations.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_module = node.module.split(".")[0]
                if top_module in HEAVY_MODULES:
                    violations.append((node.module, node.lineno))

    return violations


# Each tuple: (relative path from APP_ROOT, set of modules that must be lazy)
LAZY_IMPORT_FILES = [
    ("environment/graph_manager.py", {"osmnx"}),
    ("services/geotiff_service.py", {"rasterio", "numpy"}),
    ("services/river_scraper_service.py", {"selenium", "pandas"}),
    ("services/dam_water_scraper_service.py", {"pandas"}),
    ("agents/routing_agent.py", {"pandas"}),
    ("database/repository.py", {"pandas"}),
    ("main.py", {"pandas"}),
]


@pytest.mark.parametrize(
    "rel_path, expected_lazy",
    LAZY_IMPORT_FILES,
    ids=[p for p, _ in LAZY_IMPORT_FILES],
)
def test_heavy_imports_are_lazy(rel_path: str, expected_lazy: set[str]):
    """Verify that heavy modules are NOT imported at module level."""
    filepath = APP_ROOT / rel_path
    assert filepath.exists(), f"Source file not found: {filepath}"

    violations = _get_module_level_imports(filepath)

    # Filter to only the modules we care about for this file
    relevant = [
        (mod, line)
        for mod, line in violations
        if mod.split(".")[0] in expected_lazy
    ]

    if relevant:
        details = "\n".join(
            f"  line {line}: import {mod}" for mod, line in relevant
        )
        pytest.fail(
            f"{rel_path} has module-level imports that should be lazy:\n{details}"
        )
