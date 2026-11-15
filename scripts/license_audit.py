#!/usr/bin/env python3
"""Screen the installed runtime requirement tree; no package imports or network calls.

Run with the project venv. --write saves both report formats; otherwise stdout only.
This is metadata evidence, not a license determination or a native-library audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from collections import deque
from datetime import date
from importlib import metadata
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
COPYLEFT_PATTERNS = (
    ("AGPL", r"\bAGPL(?:v?\d)?\b|\b(?:GNU\s+)?Affero\s+(?:General\s+Public\s+License|GPL)"),
    ("LGPL", r"\bLGPL(?:v?\d)?\b|\b(?:GNU\s+)?(?:Lesser|Library)\s+General\s+Public\s+License"),
    ("GPL", r"\bGPL(?:v?\d)?\b|\b(?:GNU\s+)?General\s+Public\s+License"),
    ("SSPL", r"\bSSPL\b|\bServer\s+Side\s+Public\s+License"),
)


def copyleft_families(text: str) -> list[str]:
    """Flag declared families, preserving alternatives/exceptions in the evidence."""
    found = []
    for family, pattern in COPYLEFT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            found.append(family)
            # Do not count the GPL inside 'Affero GPL' a second time.
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return found


def license_evidence(meta) -> dict:
    expression = (meta.get("License-Expression") or "").strip()
    license_text = (meta.get("License") or "").strip()
    classifiers = [c for c in meta.get_all("Classifier", []) if c.startswith("License ::")]
    declarations = sorted(set(re.findall(r"^\s*License:\s*(.+)$", license_text, flags=re.MULTILINE)))
    # A full license may be supplied without SPDX declarations or classifiers.
    # Recognize standalone titles, not incidental mentions in another license.
    headings = sorted(
        set(
            re.findall(
                r"^[ \t]*((?:GNU[ \t]+)?(?:(?:AFFERO|LESSER|LIBRARY)[ \t]+)?"
                r"GENERAL[ \t]+PUBLIC[ \t]+LICENSE|SERVER[ \t]+SIDE[ \t]+PUBLIC[ \t]+LICENSE)[ \t]*$",
                license_text,
                flags=re.MULTILINE | re.IGNORECASE,
            )
        )
    )
    # Long License fields often include contact details and entire bundled notices.
    # Record their explicit declarations and digest, not a public copy of that prose.
    short = " ".join(license_text.split()) if len(license_text) <= 240 else ""
    evidence = "\n".join([expression, short, *declarations, *headings, *classifiers])
    families = copyleft_families(evidence)
    display = (
        expression or short or "; ".join(declarations or headings) or "; ".join(classifiers) or "UNKNOWN"
    )
    # Display the family/version plainly while retaining the original dual-license field.
    if "AGPL" in families and re.search(r"(?:GPL\s*3(?:\.0)?|AGPL[- ]?3)", evidence, re.I):
        display = f"AGPL-3.0 family; {display}"
    return {
        "license": display,
        "license_expression": expression or None,
        "license_metadata": short or None,
        "license_declarations": declarations,
        "license_headings": headings,
        "license_classifiers": classifiers,
        "license_text_sha256": hashlib.sha256(license_text.encode()).hexdigest() if license_text else None,
        "license_text_omitted": bool(license_text and not short),
        "copyleft_families": families,
        "review": "missing license metadata"
        if display == "UNKNOWN"
        else ("review full License text" if license_text and not short and not declarations else None),
    }


def active(req: Requirement, extras: set[str], environment: dict[str, str]) -> bool:
    return req.marker is None or any(
        req.marker.evaluate({**environment, "extra": extra}) for extra in {"", *extras}
    )


def requirement_label(req: Requirement) -> str:
    """Report requirement identity without URLs or local install locations."""
    extras = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
    return f"{canonicalize_name(req.name)}{extras}{req.specifier}"


def audit(project_file: Path, lookup=metadata.distribution) -> dict:
    project = tomllib.loads(project_file.read_text(encoding="utf-8"))["project"]
    environment = default_environment()
    roots = [Requirement(text) for text in project.get("dependencies", [])]
    roots = [req for req in roots if active(req, set(), environment)]
    queue = deque((req, "project") for req in roots)
    rows: dict[str, dict] = {}
    visited = set()
    errors = set()
    while queue:
        req, parent = queue.popleft()
        name = canonicalize_name(req.name)
        if name not in rows:
            try:
                dist = lookup(name)
            except metadata.PackageNotFoundError:
                rows[name] = {
                    "name": name,
                    "version": None,
                    "license": "UNKNOWN (not installed)",
                    "copyleft_families": [],
                    "required_by": [],
                    "requires": [],
                    "review": "missing distribution",
                }
                errors.add(f"{name}: not installed")
            else:
                rows[name] = {
                    "name": name,
                    "version": dist.version,
                    **license_evidence(dist.metadata),
                    "required_by": [],
                    "requires": [],
                }
        row = rows[name]
        if parent not in row["required_by"]:
            row["required_by"].append(parent)
        if row["version"] is None:
            continue
        if req.specifier and not req.specifier.contains(row["version"], prereleases=True):
            errors.add(f"{name}: installed {row['version']} does not satisfy {req.specifier}")
        context = (name, frozenset(req.extras))
        if context in visited:
            continue
        visited.add(context)
        for child_text in lookup(name).requires or []:
            child = Requirement(child_text)
            if active(child, set(req.extras), environment):
                label = requirement_label(child)
                if label not in row["requires"]:
                    row["requires"].append(label)
                queue.append((child, name))
    for row in rows.values():
        row["required_by"].sort()
        row["requires"].sort()
    return {
        "generated_on": date.today().isoformat(),
        "scope": "project.dependencies and active transitive Requires-Dist; no root optional extras",
        "environment": {
            key: environment[key] for key in ("python_full_version", "sys_platform", "platform_machine")
        },
        "roots": sorted(requirement_label(req) for req in roots),
        "packages": [rows[name] for name in sorted(rows)],
        "errors": sorted(errors),
    }


def markdown(report: dict) -> str:
    def cell(value: str) -> str:
        return " ".join(value.split()).replace("|", "\\|")

    lines = [
        "# Installed dependency licenses",
        "",
        f"Generated: {report['generated_on']} with `importlib.metadata`.",
        "",
        f"Scope: {report['scope']}.",
        "Environment: " + ", ".join(f"{k}={v}" for k, v in report["environment"].items()) + ".",
        "",
        "Reproduce: `.venv/bin/python scripts/license_audit.py --format md --write`.",
        "JSON evidence: [dependency-licenses.json](dependency-licenses.json).",
        "",
        "AGPL/GPL/LGPL/SSPL flags screen declarations, not legal obligations. Alternatives and exceptions",
        "remain in the license column. 'none detected' does not mean permissive: MPL and other licenses",
        "are outside this flag set. UNKNOWN requires review. Long License fields are represented by",
        "explicit declarations/titles, classifiers, and a SHA-256 digest in JSON, without full prose.",
        "This is not a complete SBOM: native bundled libraries, license files, build/test/docs extras,",
        "webapp-only and frontend dependencies, and the optional PDFium spike are outside this tree.",
        "See [HOSTING.md](HOSTING.md) for the dated source review and limitations.",
        "",
        "| Name | Version | License metadata / expression | License classifiers | Copyleft flag | Required by |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["packages"]:
        values = [
            row["name"],
            row["version"] or "MISSING",
            row["license"],
            "; ".join(row.get("license_classifiers", [])) or "not supplied",
            ", ".join(row["copyleft_families"]) or "none detected",
            ", ".join(row["required_by"]),
        ]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    reviews = [f"{r['name']}: {r['review']}" for r in report["packages"] if r.get("review")]
    lines += ["", "Review items: " + ("; ".join(reviews) or "none in metadata") + "."]
    lines += ["", "Resolution errors: " + ("; ".join(report["errors"]) or "none") + ".", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("md", "json"), default="md")
    parser.add_argument("--write", action="store_true", help="write both formats to docs/licensing")
    args = parser.parse_args()
    report = audit(ROOT / "pyproject.toml")
    rendered = {"md": markdown(report), "json": json.dumps(report, indent=2) + "\n"}
    if args.write:
        out = ROOT / "docs" / "licensing"
        out.mkdir(parents=True, exist_ok=True)
        for fmt, content in rendered.items():
            (out / f"dependency-licenses.{fmt}").write_text(content, encoding="utf-8")
    sys.stdout.write(rendered[args.format])
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
