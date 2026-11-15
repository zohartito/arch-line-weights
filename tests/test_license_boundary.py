"""Guard named/literal imports and the webapp's current startup import graph.

Existing dormant webapp imports are explicit exceptions, not a licensing boundary.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from importlib.util import resolve_name
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = {
    "src/arch_line_weights/preview.py",
    "src/arch_line_weights/inspect.py",
    # Standalone local text/outline indexer; documented in docs/licensing/HOSTING.md.
    "scripts/build_reference_index.py",
}
# pymupdf4llm and pymupdf_layout are installed alongside PyMuPDF and import it.
FORBIDDEN = {"pymupdf", "fitz", "pymupdfb", "pymupdf4llm", "pymupdf_layout"}
WEBAPP_FORBIDDEN = {"arch_line_weights.inspect", "arch_line_weights.preview"}
WEBAPP_ALLOWLIST = {
    # Dormant job pipeline: inspect_file calls at line 151 can load PyMuPDF.
    ("webapp/backend/compute.py", 27, "arch_line_weights.inspect.inspect_file"),
    # Dormant console pipeline: inspect_file calls at lines 322 and 800 can load PyMuPDF.
    ("webapp/backend/console.py", 25, "arch_line_weights.inspect.inspect_file"),
}


def named_imports(source: str, package: str = "") -> list[tuple[int, str]]:
    """Read imports at every depth, including literal calls and importlib aliases.

    This is a drift check for ordinary imports, not a barrier to deliberate evasion:
    computed module names, arbitrary callable rebinding, a reassigned ``__package__``
    and ``__import__`` calls that pass ``globals``/``level`` are outside this scan.
    """
    tree = ast.parse(source)
    importlib_names = {"importlib"}
    import_module_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            importlib_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "importlib"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib" and not node.level:
            import_module_names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "import_module"
            )

    def absolute(name, context):
        if name.startswith(".") and context:
            try:
                return resolve_name(name, context)
            except (ImportError, ValueError):
                pass
        return name.lstrip(".")

    def argument(node, index, keyword):
        if len(node.args) > index:
            return node.args[index]
        return next((arg.value for arg in node.keywords if arg.arg == keyword), None)

    imports = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = absolute("." * node.level + (node.module or ""), package)
            names = [f"{base}.{alias.name}".lstrip(".") for alias in node.names]
        elif isinstance(node, ast.Call):
            builtin = isinstance(node.func, ast.Name) and node.func.id == "__import__"
            dynamic = (isinstance(node.func, ast.Name) and node.func.id in import_module_names) or (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in importlib_names
                and node.func.attr == "import_module"
            )
            name = argument(node, 0, "name")
            if (builtin or dynamic) and isinstance(name, ast.Constant) and isinstance(name.value, str):
                context = argument(node, 1, "package") if dynamic else None
                base = absolute(
                    name.value,
                    context.value
                    if isinstance(context, ast.Constant) and isinstance(context.value, str)
                    else package,
                )
                names = [base]
                fromlist = argument(node, 3, "fromlist") if builtin else None
                if isinstance(fromlist, (ast.List, ast.Tuple)):
                    names.extend(
                        f"{base}.{item.value}"
                        for item in fromlist.elts
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    )
        imports.extend((node.lineno, name) for name in names if name)
    return sorted(set(imports))


def webapp_imports(source: str, package: str = "") -> list[tuple[int, str]]:
    return [
        (line, name)
        for line, name in named_imports(source, package)
        if any(name == target or name.startswith(target + ".") for target in WEBAPP_FORBIDDEN)
    ]


def pymupdf_imports(source: str) -> list[int]:
    return sorted({line for line, name in named_imports(source) if name.split(".")[0] in FORBIDDEN})


def python_files(directory: str):
    for path in sorted((ROOT / directory).rglob("*.py")):
        if not {".venv", "node_modules", "__pycache__"}.intersection(path.relative_to(ROOT).parts):
            yield path


def test_pymupdf_imports_stay_in_allowlist():
    violations = []
    for directory in ("src", "webapp", "scripts"):
        for path in python_files(directory):
            relative = path.relative_to(ROOT).as_posix()
            if relative not in ALLOWLIST:
                violations.extend(
                    f"{relative}:{line}" for line in pymupdf_imports(path.read_text(encoding="utf-8"))
                )
    assert not violations, "PyMuPDF imports outside the reviewed allowlist: " + ", ".join(violations)


def test_webapp_imports_stay_at_existing_call_sites():
    found = {
        (path.relative_to(ROOT).as_posix(), line, name)
        for path in python_files("webapp")
        for line, name in webapp_imports(path.read_text(encoding="utf-8"))
    }
    assert found == WEBAPP_ALLOWLIST, (
        f"Unexpected webapp imports: {sorted(found - WEBAPP_ALLOWLIST)}; "
        f"stale exceptions: {sorted(WEBAPP_ALLOWLIST - found)}"
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import pymupdf as pdf", [1]),
        ("import os, fitz", [1]),
        ("import pymupdf4llm", [1]),
        ("from pymupdf_layout import activate", [1]),
        ('importlib.import_module("pymupdf4llm.helpers")', [1]),
        ("from pymupdf.utils import getColor", [1]),
        ("def render():\n    from fitz import open", [2]),
        ('importlib.import_module("pymupdf")', [1]),
        ('def render():\n    importlib.import_module("fitz.utils")', [2]),
        ('__import__("pymupdf")', [1]),
        ('__import__(name="fitz")', [1]),
        ('import importlib as loader\nloader.import_module("fitz")', [2]),
        ('from importlib import import_module as load\nload("pymupdf")', [2]),
        ("# import pymupdf\nmessage = 'import fitz'", []),
        ("import pikepdf\nfrom arch_line_weights.inspect import inspect_file", []),
    ],
)
def test_ast_scan_recognizes_imports(source, expected):
    assert pymupdf_imports(source) == expected


@pytest.mark.parametrize("module", ["inspect", "preview"])
@pytest.mark.parametrize(
    "statement",
    [
        "import arch_line_weights.{module}",
        "import arch_line_weights.{module} as helper",
        "from arch_line_weights import {module} as helper",
        "from arch_line_weights.{module} import helper",
        "from .arch_line_weights import {module}",
        "from ..arch_line_weights.{module} import helper",
        'importlib.import_module("arch_line_weights.{module}")',
        'importlib.import_module(".{module}", package="arch_line_weights")',
        '__import__("arch_line_weights.{module}")',
        '__import__("arch_line_weights", fromlist=["{module}"])',
        '__import__("arch_line_weights", {{}}, {{}}, ("{module}",))',
    ],
)
@pytest.mark.parametrize("lazy", [False, True])
def test_webapp_scan_recognizes_import_forms(statement, module, lazy):
    source = statement.format(module=module)
    if lazy:
        source = "def handler():\n    " + source
    imports = webapp_imports(source)
    assert len(imports) == 1
    line, name = imports[0]
    assert line == (2 if lazy else 1)
    assert name.startswith(f"arch_line_weights.{module}")


def test_relative_import_uses_package_context():
    assert webapp_imports("from . import inspect", "arch_line_weights") == [(1, "arch_line_weights.inspect")]
    assert webapp_imports("from ..preview import helper", "arch_line_weights.handlers") == [
        (1, "arch_line_weights.preview.helper")
    ]


def test_webapp_scan_ignores_unrelated_names_and_prose():
    assert (
        webapp_imports(
            "import inspect\nfrom . import inspect\nfrom arch_line_weights import presets\n"
            'message = "arch_line_weights.preview"\n# import arch_line_weights.inspect\n'
            'importlib.import_module("arch_line_weights.preview_utils")'
        )
        == []
    )


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
                if name.split('.')[0] in {'pymupdf', 'fitz', 'pymupdfb', 'pymupdf4llm', 'pymupdf_layout'})
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
