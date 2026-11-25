"""ALW-25: the optional frontend's locked toolchain is past the 2026-11-15 audit ranges, and CI audits dev deps."""

import json
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[1] / "webapp" / "frontend"


def _locked(name: str) -> tuple[int, ...]:
    lock = json.loads((FRONTEND / "package-lock.json").read_text(encoding="utf-8"))
    version = lock["packages"][f"node_modules/{name}"]["version"]
    return tuple(int(part) for part in version.split("-")[0].split("."))


def test_alw25_locked_toolchain_is_past_audited_ranges():
    # Ranges from `npm audit --include=dev` on the previous lock (23 advisories, 1 critical).
    assert _locked("vite") > (6, 4, 3)
    assert _locked("svelte") > (5, 55, 6)
    assert _locked("@sveltejs/adapter-vercel") >= (7, 0, 3)
    assert _locked("postcss") > (8, 5, 22)
    assert _locked("devalue") > (5, 9, 2)
    lock = json.loads((FRONTEND / "package-lock.json").read_text(encoding="utf-8"))
    assert not [
        path
        for path in lock["packages"]
        if path.endswith("node_modules/tar")
        and tuple(int(p) for p in lock["packages"][path]["version"].split(".")) <= (7, 5, 20)
    ]


def test_alw25_ci_audits_frontend_including_dev_dependencies():
    ci = (FRONTEND.parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "working-directory: webapp/frontend" in ci
    assert "npm ci --ignore-scripts" in ci
    assert "npm audit --include=dev --audit-level=moderate" in ci
