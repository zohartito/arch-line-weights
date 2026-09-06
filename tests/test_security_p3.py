"""Focused regression coverage for the retained P3 security boundaries."""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from arch_line_weights.classify import MAX_MAPPING_WEIGHT_PT, from_user_mapping
from arch_line_weights.proof import (
    ManifestValidationError,
    ReviewRegion,
    _parse_review_regions,
    _synthetic_image_size,
)
from arch_line_weights.safety import (
    cleanup_private_temp_dir,
    open_private_temp_file,
    private_temp_dir,
    private_temp_directory,
    terminal_safe,
)


def _load_benchmark_module():
    path = Path(__file__).parents[1] / "scripts" / "benchmark.py"
    spec = importlib.util.spec_from_file_location("arch_lw_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_mapping_rejects_nonfinite_nonpositive_and_extreme_weights() -> None:
    for value in (float("nan"), float("inf"), -float("inf"), 0, -0.1, True, "0.25", 10**100000):
        with pytest.raises(ValueError, match="finite"):
            from_user_mapping({(1, 2, 3): value})

    with pytest.raises(ValueError, match="at most 100 pt"):
        from_user_mapping({(1, 2, 3): MAX_MAPPING_WEIGHT_PT + 1})

    assert from_user_mapping({(1, 2, 3): 0.25}) == {(1, 2, 3): 0.25}


def test_private_temp_directory_is_not_shared_or_world_accessible() -> None:
    first = private_temp_dir(prefix="arch-lw-test-")
    second = private_temp_dir(prefix="arch-lw-test-")
    try:
        assert first != second
        assert first.stat().st_mode & 0o777 == 0o700
        assert second.stat().st_mode & 0o777 == 0o700
    finally:
        cleanup_private_temp_dir(first)
        cleanup_private_temp_dir(second)


def test_private_temp_directory_cleans_after_success_and_failure() -> None:
    with private_temp_directory(prefix="arch-lw-test-") as success:
        success_marker = success
        (success / "artifact.txt").write_text("ok", encoding="utf-8")
    assert not success_marker.exists()

    with pytest.raises(RuntimeError), private_temp_directory(prefix="arch-lw-test-") as failure:
        failure_marker = failure
        raise RuntimeError("exercise cleanup")
    assert not failure_marker.exists()


def test_private_temp_file_rejects_preexisting_or_linked_targets() -> None:
    directory = private_temp_dir(prefix="arch-lw-test-")
    try:
        target = directory / "progress.txt"
        target.write_text("existing", encoding="utf-8")
        with pytest.raises(FileExistsError):
            open_private_temp_file(directory, "progress.txt")
        target.unlink()
        os.symlink("outside", target)
        with pytest.raises(FileExistsError):
            open_private_temp_file(directory, "progress.txt")
    finally:
        cleanup_private_temp_dir(directory)


def test_default_jsx_and_layout_work_dirs_are_cleaned_on_success_and_failure(monkeypatch) -> None:
    import arch_line_weights.apply_jsx as apply_jsx_module
    import arch_line_weights.layout_jsx as layout_jsx_module

    apply_dirs: list[Path] = []
    layout_dirs: list[Path] = []
    monkeypatch.setattr(apply_jsx_module, "processing_disabled", lambda _surface: None)
    monkeypatch.setattr(
        apply_jsx_module,
        "_apply_via_jsx",
        lambda *args, work_dir, **kwargs: apply_dirs.append(work_dir) or {"report": "ok"},
    )
    assert apply_jsx_module.apply_via_jsx("input.ai") == {"report": "ok"}
    assert apply_dirs and not apply_dirs[0].exists()

    monkeypatch.setattr(layout_jsx_module, "processing_disabled", lambda _surface: None)
    monkeypatch.setattr(
        layout_jsx_module,
        "_layout_via_jsx",
        lambda *args, work_dir, **kwargs: layout_dirs.append(work_dir) or {"report": "ok"},
    )
    assert layout_jsx_module.layout_via_jsx("input.ai") == {"report": "ok"}
    assert layout_dirs and layout_dirs[0] is not None and not layout_dirs[0].exists()

    monkeypatch.setattr(
        apply_jsx_module,
        "_apply_via_jsx",
        lambda *args, work_dir, **kwargs: (
            apply_dirs.append(work_dir),
            (_ for _ in ()).throw(RuntimeError("boom")),
        )[1],
    )
    with pytest.raises(RuntimeError, match="boom"):
        apply_jsx_module.apply_via_jsx("input.ai")
    assert not apply_dirs[-1].exists()

    monkeypatch.setattr(
        layout_jsx_module,
        "_layout_via_jsx",
        lambda *args, work_dir, **kwargs: (
            layout_dirs.append(work_dir),
            (_ for _ in ()).throw(RuntimeError("boom")),
        )[1],
    )
    with pytest.raises(RuntimeError, match="boom"):
        layout_jsx_module.layout_via_jsx("input.ai")
    assert layout_dirs[-1] is not None and not layout_dirs[-1].exists()


def test_terminal_safe_visibly_escapes_all_terminal_control_classes() -> None:
    rendered = terminal_safe("layer\x1b]0;title\x07\r\nnext\u0085")
    assert rendered == "layer\\x1b]0;title\\x07\\x0d\\x0anext\\x85"
    assert "\x1b" not in rendered
    assert "\x07" not in rendered
    assert "\r" not in rendered
    assert "\n" not in rendered
    assert "\u0085" not in rendered


def test_converted_document_errors_escape_active_names_at_every_stderr_path(monkeypatch) -> None:
    import arch_line_weights.apply_jsx as apply_jsx_module
    import arch_line_weights.layout_jsx as layout_jsx_module

    hostile_name = "other\x1b]0;owned\x07 [Converted].ai"
    monkeypatch.setattr(apply_jsx_module, "query_active_doc", lambda: (hostile_name, None))
    with (
        private_temp_directory(prefix="arch-lw-test-") as work_dir,
        pytest.raises(RuntimeError) as apply_error,
    ):
        apply_jsx_module._apply_via_jsx("input.ai", work_dir=work_dir)
    assert "\x1b" not in str(apply_error.value)
    assert "\\x1b" in str(apply_error.value)

    monkeypatch.setattr(layout_jsx_module, "query_active_doc", lambda: (hostile_name, None))
    with (
        private_temp_directory(prefix="arch-lw-test-") as work_dir,
        pytest.raises(RuntimeError) as layout_error,
    ):
        layout_jsx_module._layout_via_jsx("input.ai", work_dir=work_dir)
    assert "\x1b" not in str(layout_error.value)
    assert "\\x1b" in str(layout_error.value)


def test_synthetic_review_regions_fail_before_large_image_allocation() -> None:
    with pytest.raises(ManifestValidationError, match="synthetic proof image budget"):
        _synthetic_image_size([ReviewRegion("oversized", "poche", (0, 0, 5000, 10))])

    with pytest.raises(ManifestValidationError, match="synthetic image pixel budget"):
        _parse_review_regions(
            [
                {"id": "one", "kind": "poche", "rect": [0, 0, 2000, 2000]},
                {"id": "two", "kind": "poche", "rect": [0, 0, 2000, 2000]},
            ],
            "fixture",
        )


def test_benchmark_markdown_cannot_break_a_table_or_emit_html() -> None:
    benchmark = _load_benchmark_module()
    timing = benchmark.StageTiming(stage="apply-saas", error="</td>| `boom`\n<img src=x>")
    row = benchmark.FileBenchmark(
        source="input|`evil`<script>.ai",
        input_bytes=1,
        layer_count=0,
        cut_layer_count=0,
        runs=1,
        apply_saas=timing,
        apply_saas_poche=benchmark.StageTiming(stage="apply-saas --poche"),
        apply_jsx=benchmark.StageTiming(stage="apply-jsx"),
    )
    rendered = benchmark._markdown_section([row], datetime.now(UTC), 1)
    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "</td>" not in rendered
    assert "input\\|\\`evil\\`&lt;script&gt;.ai" in rendered
    assert "&lt;/td&gt;\\| \\`boom\\`<br\\>&lt;img src=x&gt;" in rendered
    assert benchmark._markdown_table_text("![label](https://example.invalid)") == (
        "\\!\\[label\\]\\(https://example.invalid\\)"
    )
