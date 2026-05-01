"""Adversarial regression tests for ``_is_converted_match`` (Issue #14).

The v0.6.1 fix in ``apply_jsx.py`` covered four common name shapes
(``<basename>.ai`` paired with ``<basename> [Converted]`` etc.), but it
missed the case where the disk filename ends with whitespace before the
extension. Concrete trigger: a Rhino-exported drawing on disk named
``wall section iso cut .ai`` (literal trailing space before ``.ai``)
opens in Illustrator as ``wall section iso cut  [Converted].ai`` (two
spaces between the stem and ``[Converted]`` because the filename's
trailing space is preserved next to Illustrator's own leading space).

The matcher must normalize whitespace on BOTH sides and still match,
otherwise apply-jsx falls through to the broken ``open POSIX file``
path and the user sees ``ERROR: target doc not open``.

These tests pin the normalization contract:

  * trailing whitespace in the disk basename is ignored
  * trailing whitespace in the active doc's stem (after peeling
    ``[Converted]``) is ignored
  * tabs and Unicode whitespace (NBSP) count as whitespace
  * multiple internal spaces inside the legitimate stem are preserved
    (those are NOT trailing whitespace)
  * a saved doc whose name does NOT contain ``[Converted]`` is rejected
    even when its path equals ``src`` — the wrapper relies on this False
    return to fall through to the standard `open POSIX file` path.
"""

from __future__ import annotations

import pytest

from arch_line_weights.apply_jsx import (
    _is_converted_match,
    _normalize_stem,
    _strip_converted_decoration,
)

# --------------------------------------------------------------------------- #
# The headline case from Issue #14
# --------------------------------------------------------------------------- #


def test_trailing_space_in_disk_filename_matches_double_space_active_name():
    """Disk file ``wall section iso cut .ai`` (trailing space before ``.ai``)
    opens in Illustrator as ``wall section iso cut  [Converted].ai`` —
    two spaces between stem and ``[Converted]``.

    The pre-Issue-14 matcher missed this entirely; v0.6.1 fixes it.
    """
    assert (
        _is_converted_match(
            "wall section iso cut  [Converted].ai",
            None,
            "/path/wall section iso cut .ai",
        )
        is True
    )


def test_trailing_space_match_with_no_extension_in_active_name():
    """Some Illustrator versions display ``[Converted]`` without
    re-appending ``.ai``. The trailing-space variant must still match."""
    assert (
        _is_converted_match(
            "wall section iso cut  [Converted]",
            None,
            "/path/wall section iso cut .ai",
        )
        is True
    )


# --------------------------------------------------------------------------- #
# Adversarial whitespace forms
# --------------------------------------------------------------------------- #


def test_leading_space_in_active_doc_name():
    """A leading space in the active-doc name (osascript artifact) must
    not break the match."""
    assert (
        _is_converted_match(
            " macro [Converted].ai",
            None,
            "/path/macro.ai",
        )
        is True
    )


def test_multiple_internal_spaces_in_legit_stem():
    """Multiple intentional internal spaces inside the stem are NOT
    trailing whitespace and must be preserved when comparing."""
    assert (
        _is_converted_match(
            "multi  internal  spaces [Converted].ai",
            None,
            "/path/multi  internal  spaces.ai",
        )
        is True
    )
    # And mismatched internal spacing must NOT match (would change the
    # actual stem identity, not just trailing whitespace).
    assert (
        _is_converted_match(
            "multi internal spaces [Converted].ai",
            None,
            "/path/multi  internal  spaces.ai",
        )
        is False
    )


def test_tab_character_is_treated_as_trailing_whitespace():
    """A tab character before the extension must be normalized away."""
    assert (
        _is_converted_match(
            "drawing\t [Converted].ai",
            None,
            "/path/drawing\t.ai",
        )
        is True
    )


def test_unicode_nbsp_is_treated_as_trailing_whitespace():
    """Non-breaking space (U+00A0) ranks as Unicode whitespace and must be
    normalized away when it appears as trailing space."""
    nbsp = " "
    assert (
        _is_converted_match(
            f"drawing{nbsp} [Converted].ai",
            None,
            f"/path/drawing{nbsp}.ai",
        )
        is True
    )


def test_mixed_whitespace_run_normalized():
    """A mix of space + tab + NBSP at the end of the stem must all
    normalize away."""
    assert (
        _is_converted_match(
            "drawing \t  [Converted].ai",
            None,
            "/path/drawing \t .ai",
        )
        is True
    )


# --------------------------------------------------------------------------- #
# False-positive guards — must NOT match when stems genuinely differ
# --------------------------------------------------------------------------- #


def test_unrelated_basename_does_not_match_even_with_converted():
    """A `[Converted]` doc with a different basename must NOT match."""
    assert (
        _is_converted_match(
            "other_drawing [Converted].ai",
            None,
            "/path/wall section iso cut .ai",
        )
        is False
    )


def test_saved_doc_without_converted_token_does_not_match():
    """A regular saved doc (no `[Converted]`) must NOT match — the
    wrapper falls through to the normal `open POSIX file` path. This
    holds even when the active doc's saved path equals ``src``."""
    assert (
        _is_converted_match(
            "macro.ai",
            "/path/macro.ai",
            "/path/macro.ai",
        )
        is False
    )


def test_converted_with_path_pointing_to_different_file_rejected():
    """If the active doc has a saved path to a *different* file, reject
    even when the basename + [Converted] match."""
    assert (
        _is_converted_match(
            "macro [Converted].ai",
            "/path/other.ai",
            "/path/macro.ai",
        )
        is False
    )


def test_empty_stem_does_not_match():
    """``[Converted].ai`` (no stem at all) must NOT match anything — the
    decoration peeler returns an empty string, which can't equal a real
    source stem."""
    assert (
        _is_converted_match("[Converted].ai", None, "/path/macro.ai")
        is False
    )
    assert (
        _is_converted_match(" [Converted].ai", None, "/path/macro.ai")
        is False
    )


# --------------------------------------------------------------------------- #
# Helper-level coverage — the normalizer + decoration stripper
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        ("plain", "plain"),
        ("trailing space ", "trailing space"),
        ("trailing tab\t", "trailing tab"),
        ("trailing nbsp ", "trailing nbsp"),
        ("internal  spaces  ", "internal  spaces"),
        ("", ""),
    ],
)
def test_normalize_stem_strips_only_trailing_whitespace(inp, expected):
    assert _normalize_stem(inp) == expected


@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        ("macro [Converted].ai", "macro"),
        ("macro [Converted]", "macro"),
        ("wall section iso cut  [Converted].ai", "wall section iso cut"),
        ("wall section iso cut  [Converted]", "wall section iso cut"),
        ("trailing tab\t [Converted].ai", "trailing tab"),
        # No [Converted] -> falls back to plain stem (extension stripped,
        # trailing whitespace stripped).
        ("plain.ai", "plain"),
        ("plain ", "plain"),
    ],
)
def test_strip_converted_decoration_handles_known_shapes(inp, expected):
    assert _strip_converted_decoration(inp) == expected
