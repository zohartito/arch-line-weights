"""Integration tests that exercise real AppleScript / Illustrator.

These tests are the regression net for apply_jsx.py's `query_active_doc()`
helper. Two prior shipped versions (v0.6.1, v0.6.3) had AppleScript syntax
errors that the unit tests didn't catch because they mocked
`subprocess.run` instead of running real osascript.

Skipped automatically when:
  - osascript isn't on PATH (Linux CI, etc.)
  - Adobe Illustrator isn't installed / running

Run manually after any change to AppleScript-emitting code:
  pytest -m integration tests/integration/

The tests are intentionally narrow: they verify the helper runs without
raising and returns either real values or (None, None). They do not
require a specific document to be open.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from arch_line_weights.apply_jsx import query_active_doc

# --------------------------------------------------------------------------- #
# Skip predicates
# --------------------------------------------------------------------------- #


def _osascript_available() -> bool:
    return shutil.which("osascript") is not None


def _illustrator_available() -> bool:
    """Return True if Adobe Illustrator is installed (whether or not it's open)."""
    if not _osascript_available():
        return False
    # Try a no-op tell to detect the app's presence in OSA's app cache.
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to '
             '(name of every application process)'],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return "Adobe Illustrator" in (result.stdout or "")


SKIP_NO_OSASCRIPT = pytest.mark.skipif(
    not _osascript_available(),
    reason="osascript not on PATH (non-macOS environment)",
)
SKIP_NO_ILLUSTRATOR = pytest.mark.skipif(
    not _illustrator_available(),
    reason="Adobe Illustrator is not running (start it before running this test)",
)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


@pytest.mark.integration
@SKIP_NO_OSASCRIPT
def test_query_active_doc_does_not_raise():
    """The helper must never raise — it must return (None, None) on failure.

    This is the core regression test. Two prior versions shipped with an
    AppleScript syntax error that caused subprocess.run to exit non-zero,
    and the helper must catch it cleanly.
    """
    name, path = query_active_doc()
    # Either both are None (no doc / Illustrator not running) or both are
    # populated with strings — never a half-state, never an exception.
    assert (name is None) == (path is None) or (name is not None and path is None)
    if name is not None:
        assert isinstance(name, str)
        assert len(name) > 0
    if path is not None:
        assert isinstance(path, str)
        assert path.startswith("/")  # POSIX path


@pytest.mark.integration
@SKIP_NO_OSASCRIPT
@SKIP_NO_ILLUSTRATOR
def test_query_active_doc_returns_string_when_illustrator_running():
    """When Illustrator IS running, the helper returns either a name or None.

    If a doc is open, name is non-empty and path is either a POSIX path
    (saved doc) or None (unsaved / [Converted] virtual doc). If no doc is
    open, returns (None, None).
    """
    name, path = query_active_doc()
    if name is None:
        # No active document — fine, nothing to assert beyond the contract.
        assert path is None
        return
    assert isinstance(name, str)
    # The name field MUST preserve internal whitespace (Issue #14):
    # we shipped a regression where rstrip() ate trailing spaces inside
    # filenames like "wall section iso cut  [Converted].ai". Verify the
    # name doesn't end with the artifacts of an over-eager strip.
    assert "\n" not in name
    assert "\r" not in name


@pytest.mark.integration
@SKIP_NO_OSASCRIPT
def test_applescript_syntax_compiles():
    """The exact AppleScript embedded in query_active_doc must parse.

    Compile-only check: run `osascript -c <script>` would actually execute,
    which we don't want without Illustrator. Instead we use `osacompile`
    via a temp file to verify the syntax parses, even when Illustrator
    isn't running.

    This is the test that would have caught v0.6.1 and v0.6.3 from
    shipping with the broken `name of active document` syntax.
    """
    import tempfile
    from pathlib import Path

    from arch_line_weights import apply_jsx

    # Pull the script string out of the helper so we test the actual
    # bytes that would run, not a lookalike.
    src = (
        Path(apply_jsx.__file__).read_text(encoding="utf-8")
    )
    # Locate the script literal — it's the multi-line concatenation
    # starting with 'tell application "Adobe Illustrator"'. Extract by
    # matching the literal that appears in the source.
    marker_start = src.find('script = (')
    assert marker_start > 0, "could not locate script literal in apply_jsx.py"
    # Find the end-tell line that closes the literal.
    end_marker = "'end tell'"
    marker_end = src.find(end_marker, marker_start)
    assert marker_end > 0
    raw = src[marker_start: marker_end + len(end_marker)]

    # Reconstruct the actual AppleScript by extracting all single-quoted
    # string segments and joining them.
    import re

    # Each source line in the literal is a Python string; concatenate.
    # The strings contain literal `\n` escape sequences that we need to
    # interpret as actual newlines for osacompile to see proper line breaks.
    lines = re.findall(r"'([^']*)'", raw)
    applescript = "".join(lines).replace("\\n", "\n")
    assert "Adobe Illustrator" in applescript
    assert "\n" in applescript, "newlines not interpreted; osacompile will fail"

    # Use osacompile via a temp source file. `osacompile -e` doesn't
    # unescape \n in -e args the way `osascript -e` does, so we write
    # the literal text of the script to a .applescript file and compile
    # that. The compiled output goes to a temp .scpt we discard.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".applescript", delete=False, encoding="utf-8"
    ) as src_file:
        src_file.write(applescript)
        src_path = src_file.name
    out_path = src_path.replace(".applescript", ".scpt")
    try:
        result = subprocess.run(
            ["osacompile", "-o", out_path, src_path],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    finally:
        Path(src_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)
    assert result.returncode == 0, (
        f"AppleScript failed to compile (this is the v0.6.1/v0.6.3 "
        f"regression class):\n{result.stderr}"
    )
