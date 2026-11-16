"""Verify default collection policy with a synthetic desktop-test sentinel."""

import subprocess
import sys
from pathlib import Path


def test_alwn3_plain_pytest_never_imports_desktop_tests(tmp_path):
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "pyproject.toml").write_bytes((root / "pyproject.toml").read_bytes())
    desktop = tmp_path / "tests" / "integration"
    desktop.mkdir(parents=True)
    (desktop / "test_probe.py").write_text('raise RuntimeError("desktop module imported")\n')
    (tmp_path / "tests" / "test_offline.py").write_text("def test_offline():\n    assert True\n")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "desktop module imported" not in result.stdout
    assert "1 test collected" in result.stdout
