"""CLI and webapp dependency artifacts must be covered by the reviewed lock."""

import re
import tomllib
from pathlib import Path


def test_alw43_workspace_lock_covers_cli_webapp_and_registry_hashes():
    root = Path(__file__).parents[1]
    lock = tomllib.loads((root / "uv.lock").read_text())
    packages = {package["name"]: package for package in lock["package"]}
    assert "arch-line-weights-webapp" in packages
    for folder, name in [(root, "arch-line-weights"), (root / "webapp", "arch-line-weights-webapp")]:
        project = tomllib.loads((folder / "pyproject.toml").read_text())["project"]
        required = {re.split(r"[\[<>=!~; ]", dependency)[0].lower() for dependency in project["dependencies"]}
        locked = {dependency["name"] for dependency in packages[name]["dependencies"]}
        assert required <= locked
    for package in packages.values():
        if "registry" in package["source"]:
            artifacts = package.get("wheels", []) + ([package["sdist"]] if "sdist" in package else [])
            assert artifacts, package["name"]
            assert all(re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["hash"]) for artifact in artifacts)
