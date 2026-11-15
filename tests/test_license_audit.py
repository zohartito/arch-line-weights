"""Exercise dependency traversal and license evidence without installing fixtures."""

from __future__ import annotations

import importlib.util
from email.message import Message
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "license_audit", Path(__file__).resolve().parents[1] / "scripts" / "license_audit.py"
)
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)


def distribution(*, requires=(), version="1.0", **fields):
    meta = Message()
    for key, value in fields.items():
        for item in value if isinstance(value, list) else [value]:
            meta[key] = item
    return SimpleNamespace(version=version, metadata=meta, requires=requires)


@pytest.mark.parametrize(
    ("text", "families"),
    [
        ("Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License", ["AGPL"]),
        ("GNU Lesser General Public License v2 (LGPLv2)", ["LGPL"]),
        ("GPL-3.0-or-later WITH GCC-exception-3.1", ["GPL"]),
        ("SSPL-1.0 OR Apache-2.0", ["SSPL"]),
        ("BSD-3-Clause AND MPL-2.0", []),
    ],
)
def test_family_flags_do_not_hide_alternatives_or_exceptions(text, families):
    row = audit_module.license_evidence(distribution(License=text).metadata)
    assert row["copyleft_families"] == families
    assert row["license_metadata"] == text


def test_license_expression_and_classifiers_both_contribute():
    dist = distribution(
        **{
            "License-Expression": "MIT OR GPL-2.0-only",
            "Classifier": ["Topic :: Utilities", "License :: OSI Approved :: MIT License"],
        }
    )
    row = audit_module.license_evidence(dist.metadata)
    assert row["license"] == "MIT OR GPL-2.0-only"
    assert row["license_classifiers"] == ["License :: OSI Approved :: MIT License"]
    assert row["copyleft_families"] == ["GPL"]


def test_long_bundled_license_retains_declarations_and_digest():
    text = "attribution prose\n" * 30 + "License: LGPL-2.1-or-later\nLicense: BSD-3-Clause\n"
    row = audit_module.license_evidence(distribution(License=text).metadata)
    assert row["license_text_omitted"]
    assert row["license_metadata"] is None
    assert len(row["license_text_sha256"]) == 64
    assert row["copyleft_families"] == ["LGPL"]
    assert "attribution prose" not in str(row)


def test_missing_license_is_unknown():
    row = audit_module.license_evidence(distribution().metadata)
    assert row["license"] == "UNKNOWN"
    assert row["review"] == "missing license metadata"


def test_full_license_title_flags_family_without_incidental_references():
    text = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n" + "license terms\n" * 30
    text += "Combining with the GNU Affero General Public License is discussed here.\n"
    row = audit_module.license_evidence(distribution(License=text).metadata)
    assert row["copyleft_families"] == ["GPL"]
    assert row["license_headings"] == ["GNU GENERAL PUBLIC LICENSE"]
    assert row["review"] == "review full License text"


def test_tree_markers_extras_cycles_and_missing_dependency(tmp_path):
    project = tmp_path / "pyproject.toml"
    project.write_text(
        '[project]\nname="demo"\ndependencies=["Root_Pkg>=1", "root-pkg[render]", "missing"]\n'
        '[project.optional-dependencies]\ntest=["not-in-runtime"]\n',
        encoding="utf-8",
    )
    installed = {
        "root-pkg": distribution(
            requires=[
                "child>=2",
                "renderer; extra == 'render'",
                "ignored; python_version < '1.0'",
            ],
            License="MIT",
        ),
        "child": distribution(requires=["root-pkg"], version="2.0", License="BSD-3-Clause"),
        "renderer": distribution(License="AGPL-3.0-only"),
    }

    def lookup(name):
        if name not in installed:
            raise metadata.PackageNotFoundError(name)
        return installed[name]

    report = audit_module.audit(project, lookup=lookup)
    rows = {row["name"]: row for row in report["packages"]}
    assert sorted(rows) == ["child", "missing", "renderer", "root-pkg"]
    assert rows["root-pkg"]["required_by"] == ["child", "project"]
    assert rows["renderer"]["copyleft_families"] == ["AGPL"]
    assert report["errors"] == ["missing: not installed"]
    assert "UNKNOWN (not installed)" in audit_module.markdown(report)


def test_installed_version_mismatch_is_reported(tmp_path):
    project = tmp_path / "pyproject.toml"
    project.write_text('[project]\ndependencies=["demo>=2"]\n', encoding="utf-8")
    report = audit_module.audit(project, lookup=lambda name: distribution(License="MIT"))
    assert report["errors"] == ["demo: installed 1.0 does not satisfy >=2"]
