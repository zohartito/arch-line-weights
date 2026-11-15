"""Guard direct PyMuPDF imports and the webapp's current startup import graph.

This does not establish a licensing boundary for future request handlers.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = {
    "src/arch_line_weights/preview.py",
    "src/arch_line_weights/inspect.py",
}
FORBIDDEN = {"pymupdf", "fitz", "pymupdfb"}


def pymupdf_imports(source: str) -> list[int]:
    violations = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        if any(name.split(".")[0] in FORBIDDEN for name in names):
            violations.append(node.lineno)
    return violations


def test_pymupdf_imports_stay_in_allowlist():
    violations = []
    for directory in ("src", "webapp"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            if {".venv", "node_modules", "__pycache__"}.intersection(path.relative_to(ROOT).parts):
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative not in ALLOWLIST:
                violations.extend(
                    f"{relative}:{line}" for line in pymupdf_imports(path.read_text(encoding="utf-8"))
                )
    assert not violations, "PyMuPDF imports outside the reviewed allowlist: " + ", ".join(violations)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import pymupdf as pdf", [1]),
        ("import os, fitz", [1]),
        ("from pymupdf.utils import getColor", [1]),
        ("def render():\n    from fitz import open", [2]),
        ("# import pymupdf\nmessage = 'import fitz'", []),
        ("import pikepdf\nfrom arch_line_weights.inspect import inspect_file", []),
    ],
)
def test_ast_scan_recognizes_imports(source, expected):
    assert pymupdf_imports(source) == expected


def test_webapp_startup_does_not_load_pymupdf(tmp_path):
    # -I gives a fresh interpreter, independent of pytest's already-imported modules.
    # A temporary cwd avoids reading a developer .env during settings construction.
    code = """
import importlib.util
import json
import sys
sys.path.insert(0, sys.argv[1])
missing = [name for name in ('fastapi', 'pydantic', 'pydantic_settings')
           if importlib.util.find_spec(name) is None]
if missing:
    print(json.dumps({'missing_webapp_dependencies': missing}))
    sys.exit(77)
import webapp.backend.main
loaded = sorted(name for name in sys.modules
                if name.split('.')[0] in {'pymupdf', 'fitz', 'pymupdfb'})
print(json.dumps({'loaded': loaded}))
"""
    env = {key: value for key, value in os.environ.items() if not key.startswith("ARCHLW_")}
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(ROOT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode == 77:
        missing = json.loads(result.stdout)["missing_webapp_dependencies"]
        pytest.skip("webapp startup dependencies not installed: " + ", ".join(missing))
    # Other import failures, including a missing PyMuPDF import, must fail rather than skip.
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["loaded"] == [], result.stdout
