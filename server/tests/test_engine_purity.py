"""The moat lock (BUILD_PLAN §6): ``engine/drawback/`` must import ONLY the standard library.

If the engine ever acquires a third-party dependency — or, worst case, imports the DB / app layer —
this test fails. That is the structural guarantee that the auditable, pure-stdlib engine core (and its
112-test suite) stays clean and sellable as the application grows around it.
"""
from __future__ import annotations

import ast
import importlib.util

from server.config import REPO_ROOT

ENGINE_PKG = REPO_ROOT / "engine" / "drawback"
INTERNAL_ROOT = "drawback"  # the engine's own package — not third-party


def _imported_roots() -> set[str]:
    roots: set[str] = set()
    for path in sorted(ENGINE_PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue  # intra-package relative import
                if node.module:
                    roots.add(node.module.split(".")[0])
    return roots


def _is_third_party(root: str) -> bool:
    if root == INTERNAL_ROOT:
        return False
    try:
        spec = importlib.util.find_spec(root)
    except (ImportError, ValueError):
        return False
    if spec is None or spec.origin in (None, "built-in", "frozen"):
        return False  # builtin/frozen ⇒ stdlib
    origin = spec.origin or ""
    return "site-packages" in origin or "dist-packages" in origin


def test_engine_imports_only_stdlib():
    offenders = sorted(r for r in _imported_roots() if _is_third_party(r))
    assert not offenders, (
        "engine/drawback/ must depend on the standard library only (the moat); "
        f"found third-party imports: {offenders}"
    )
