"""Regression tests for paths crossing AppleScript and JSX boundaries."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from arch_line_weights.apply_jsx import open_in_illustrator, render_jsx, run_jsx_in_illustrator
from arch_line_weights.poche import (
    _osascript_open,
    _osascript_run_jsx,
    render_apply_jsx,
    render_dump_jsx,
)

HOSTILE_PATH = '/tmp/drawing"\\nreturn & do shell script "false" & ".ai'


def test_apply_renderer_serializes_every_path_as_a_javascript_string() -> None:
    paths = [f"{HOSTILE_PATH}-{index}\u2028" for index in range(5)]

    rendered = render_jsx(*paths)

    declarations = ("TARGET", "OUTPUT", "PROGRESS", "REPORT", "HEART")
    for declaration, value in zip(declarations, paths, strict=True):
        assert f"var {declaration}" in rendered
        assert json.dumps(value, ensure_ascii=True) in rendered
        assert value not in rendered


def test_poche_renderers_serialize_paths_as_javascript_strings() -> None:
    target = f"{HOSTILE_PATH}-target\u2028"
    output = f"{HOSTILE_PATH}-output\u2029"
    report = f"{HOSTILE_PATH}-report\r"

    dump_rendered = render_dump_jsx(target, report)
    apply_rendered = render_apply_jsx(target, output, report, {})

    for rendered, values in (
        (dump_rendered, (target, report)),
        (apply_rendered, (target, output, report)),
    ):
        for value in values:
            assert json.dumps(value, ensure_ascii=True) in rendered
            assert value not in rendered


@pytest.mark.parametrize(
    ("runner", "timeout"),
    (
        (open_in_illustrator, 1800),
        (run_jsx_in_illustrator, 3600),
        (_osascript_open, 1800),
        (_osascript_run_jsx, 1800),
    ),
)
def test_osascript_receives_paths_as_argv_not_source(runner, timeout: int) -> None:
    path = f"{HOSTILE_PATH}-argv"

    with patch("subprocess.run") as subprocess_run:
        runner(path)

    command = subprocess_run.call_args.args[0]
    assert command[:2] == ["osascript", "-e"]
    assert "on run argv" in command[2]
    assert path not in command[2]
    assert command[-2:] == ["--", path]
    assert subprocess_run.call_args.kwargs["check"] is True
    assert subprocess_run.call_args.kwargs["timeout"] >= timeout
