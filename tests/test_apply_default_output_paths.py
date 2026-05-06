"""Regression tests for Issue #12 — distinct default output paths.

Symptom: both ``apply-jsx`` and ``apply-saas`` defaulted to
``<src> HIERARCHY.<ext>``. Running both on the same source raced; the
slower pipeline silently overwrote the faster one.

Fix:

  * ``apply-jsx``  -> ``<src> HIERARCHY-jsx.<ext>``
  * ``apply-saas`` -> ``<src> HIERARCHY-saas.<ext>``
  * legacy ``apply`` (pikepdf, layer-flattening) -> ``<src> HIERARCHY.<ext>``
    (kept for back-compat with users who have scripts pinned to it)

These tests assert:

  1. The two helper functions return distinct paths for the same source.
  2. Each command's ``--help`` advertises the new suffix.
  3. The legacy ``apply`` command's ``--help`` still shows the bare
     ``HIERARCHY`` suffix (no behaviour change there).
"""

from __future__ import annotations

from click.testing import CliRunner

from arch_line_weights.apply_jsx import (
    DEFAULT_OUTPUT_SUFFIX as JSX_SUFFIX,
)
from arch_line_weights.apply_jsx import (
    default_output_path as default_output_path_jsx,
)
from arch_line_weights.apply_saas import (
    DEFAULT_OUTPUT_SUFFIX as SAAS_SUFFIX,
)
from arch_line_weights.apply_saas import (
    default_output_path as default_output_path_saas,
)
from arch_line_weights.cli import cli

# --------------------------------------------------------------------------- #
# Helper-level: the two default-path functions return distinct paths
# --------------------------------------------------------------------------- #


def test_default_output_paths_are_distinct_for_ai():
    src = "/some/dir/macro.ai"
    jsx = default_output_path_jsx(src)
    saas = default_output_path_saas(src)
    assert jsx != saas
    assert jsx.endswith("macro HIERARCHY-jsx.ai")
    assert saas.endswith("macro HIERARCHY-saas.ai")


def test_default_output_paths_are_distinct_for_pdf():
    src = "/some/dir/macro.pdf"
    jsx = default_output_path_jsx(src)
    saas = default_output_path_saas(src)
    assert jsx != saas
    assert jsx.endswith("macro HIERARCHY-jsx.pdf")
    assert saas.endswith("macro HIERARCHY-saas.pdf")


def test_default_output_paths_preserve_directory():
    """The default goes next to the source, not in CWD."""
    src = "/some/where/specific/foo.ai"
    assert default_output_path_jsx(src).startswith("/some/where/specific/")
    assert default_output_path_saas(src).startswith("/some/where/specific/")


def test_suffix_constants_are_what_we_expect():
    """Pin the literal suffixes so future renames notice this test."""
    assert JSX_SUFFIX == " HIERARCHY-jsx"
    assert SAAS_SUFFIX == " HIERARCHY-saas"


def test_default_output_paths_handle_pathlike():
    """Both helpers must accept any os.PathLike — exercised via
    ``pathlib.Path`` to ensure no implicit string-only assumption."""
    from pathlib import Path

    src = Path("/some/dir/macro.ai")
    assert default_output_path_jsx(src).endswith("macro HIERARCHY-jsx.ai")
    assert default_output_path_saas(src).endswith("macro HIERARCHY-saas.ai")


# --------------------------------------------------------------------------- #
# CLI --help advertises the new defaults
# --------------------------------------------------------------------------- #


def _flatten_help(text: str) -> str:
    """Click wraps long help text across multiple lines (with hyphenation
    on hyphens — so ``HIERARCHY-jsx`` becomes ``HIERARCHY-\\n   jsx``).
    For substring assertions we collapse all whitespace runs to single
    spaces and remove spaces immediately after a hyphen so wrapped tokens
    re-form."""
    import re

    flat = re.sub(r"\s+", " ", text)
    # Re-glue tokens that wrapped on a hyphen, e.g. ``HIERARCHY- jsx``.
    flat = re.sub(r"-\s+", "-", flat)
    return flat


def test_apply_jsx_help_advertises_new_default():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-jsx", "--help"])
    assert result.exit_code == 0
    assert "HIERARCHY-jsx" in _flatten_help(result.output)


def test_apply_saas_help_advertises_new_default():
    runner = CliRunner()
    result = runner.invoke(cli, ["apply-saas", "--help"])
    assert result.exit_code == 0
    assert "HIERARCHY-saas" in _flatten_help(result.output)
    assert "--poche-overlay" in result.output


def test_legacy_apply_help_keeps_bare_hierarchy_suffix():
    """The legacy `apply` command (pikepdf + layer-flattening) keeps the
    bare ``HIERARCHY`` suffix for back-compat. Many users have scripts
    pinned to its current default — Issue #12 explicitly does NOT change
    it."""
    runner = CliRunner()
    result = runner.invoke(cli, ["apply", "--help"])
    assert result.exit_code == 0
    flat = _flatten_help(result.output)
    assert "HIERARCHY" in flat
    # Must NOT have picked up the new suffixes.
    assert "HIERARCHY-jsx" not in flat
    assert "HIERARCHY-saas" not in flat


# --------------------------------------------------------------------------- #
# End-to-end on a tmp source: apply-jsx and apply-saas pick distinct paths
# --------------------------------------------------------------------------- #


def test_apply_jsx_and_apply_saas_compute_different_default_outputs(tmp_path):
    """If both pipelines were run on the same source, they would land in
    distinct files. We don't actually invoke either subcommand here (they
    require pikepdf/Illustrator and a real .ai); we just confirm the two
    helper functions agree to disagree on the same input."""
    src = tmp_path / "drawing.ai"
    src.write_text("dummy")

    jsx_dst = default_output_path_jsx(str(src))
    saas_dst = default_output_path_saas(str(src))

    assert jsx_dst != saas_dst
    # Both must live next to the source, not in CWD.
    assert jsx_dst.startswith(str(tmp_path))
    assert saas_dst.startswith(str(tmp_path))
