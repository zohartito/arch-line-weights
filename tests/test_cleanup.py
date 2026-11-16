from __future__ import annotations

import json

import pikepdf
import pytest
from click.testing import CliRunner

from arch_line_weights.apply_saas import _read_payload
from arch_line_weights.cleanup import CleanupThresholds, cleanup_payload
from arch_line_weights.cli import cli
from arch_line_weights.poche_saas import CHUNK, compress_test_payload


def _single_layer_payload(
    *,
    layer: bytes = b"FIXED_STAIR_COHESIVE",
    color_line: bytes = b"0 0 0 1 0 0 0 XA\r",
) -> bytes:
    return (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(" + layer + b") Ln\r" + color_line + b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 0 m\r"
        b"0.4 0 L\r"
        b"S\r"
        b"0 10 m\r"
        b"12 10 L\r"
        b"S\r"
        b"0 20 m\r"
        b"60 20 L\r"
        b"S\r"
        b"0 30 m\r"
        b"140 30 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )


def _write_native_ai(path, payload: bytes) -> None:
    framed = compress_test_payload(payload)
    chunks = [framed[i : i + CHUNK] for i in range(0, len(framed), CHUNK)]

    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    private = pikepdf.Dictionary({"/NumBlock": len(chunks)})
    for index, chunk in enumerate(chunks, start=1):
        private[f"/AIPrivateData{index}"] = pdf.make_stream(chunk)
    page.obj["/PieceInfo"] = pikepdf.Dictionary({"/Illustrator": pikepdf.Dictionary({"/Private": private})})
    pdf.save(str(path))
    pdf.close()


def test_cleanup_payload_classifies_fixed_stair_single_layer_conservatively():
    result = cleanup_payload(
        _single_layer_payload(),
        thresholds=CleanupThresholds(
            debris_max_pt=1.0,
            detail_max_pt=24.0,
            profile_min_pt=96.0,
        ),
    )
    report = result.report.to_dict()

    assert report["summary"]["low_semantic"] is True
    assert report["summary"]["deleted"] == 1
    assert report["summary"]["lightened"] == 1
    assert report["summary"]["medium"] == 1
    assert report["summary"]["heavy"] == 1
    assert report["layers"][0]["geometric_roles"]["spatial-edge"] == 1
    assert report["layers"][0]["geometric_roles"]["surface"] >= 1
    assert "single/low-semantic layer" in report["warnings"][0]

    assert b"0.4 0 L\rS\r" not in result.payload
    assert b"\r0.18 w\r0 10 m\r12 10 L\rS\r" in result.payload
    assert b"\r0.25 w\r0 20 m\r60 20 L\rS\r" in result.payload
    assert b"\r0.5 w\r0 30 m\r140 30 L\rS\r" in result.payload


def test_cleanup_payload_removes_exact_duplicate_make2d_paths():
    payload = (
        b"%!PS-Adobe-3.0\r"
        b"%AI5_BeginLayer\r"
        b"(single_layer_axon) Ln\r"
        b"0 0 0 1 0 0 0 XA\r"
        b"1 J 1 j 1 w 4 M []0 d\r"
        b"0 0 m\r"
        b"40 0 L\r"
        b"S\r"
        b"0 0 m\r"
        b"40 0 L\r"
        b"S\r"
        b"LB\r"
        b"%AI5_EndLayer--\r"
    )

    result = cleanup_payload(payload)
    report = result.report.to_dict()

    assert report["summary"]["deleted"] == 1
    assert report["summary"]["duplicates"] == 1
    assert result.payload.count(b"40 0 L\rS\r") == 1


def test_cleanup_payload_handles_cmyk_payloads_without_color_dependency():
    payload = _single_layer_payload(
        layer=b"single_layer_axon",
        color_line=b"0.1765 0.2745 0.4314 0.1765 K\r",
    )

    result = cleanup_payload(payload)
    report = result.report.to_dict()

    assert b"0.1765 0.2745 0.4314 0.1765 K\r" in result.payload
    assert report["summary"]["stroked_paths"] == 4
    assert report["layers"][0]["name"] == "single_layer_axon"
    assert report["layers"][0]["heavy"] == 1


def test_cleanup_cli_writes_new_file_and_json_report(tmp_path):
    src = tmp_path / "single-layer.ai"
    dst = tmp_path / "single-layer CLEANUP.ai"
    report_path = tmp_path / "cleanup-report.json"
    _write_native_ai(src, _single_layer_payload())
    original = src.read_bytes()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "cleanup",
            str(src),
            "--output",
            str(dst),
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert src.read_bytes() == original
    assert dst.exists()
    assert report_path.exists()

    data = json.loads(report_path.read_text())
    assert data["summary"]["deleted"] == 1
    assert data["summary"]["heavy"] == 1
    assert data["source"]["mode"] == "cleanup"

    with pikepdf.open(dst) as pdf:
        rewritten_payload = _read_payload(pdf)
    assert b"\r0.5 w\r0 30 m\r140 30 L\rS\r" in rewritten_payload


def _audit_payload(paths):
    return b"%AI5_BeginLayer\r(AUDIT) Ln\r" + paths + b"LB\r"


def test_alw02_preserves_distinct_cubics_and_closed_loop():
    paths = (
        b"0 0 m\r10 50 40 50 50 0 C\rS\r"
        b"0 0 m\r10 -50 40 -50 50 0 C\rS\r"
        b"100 100 m\r300 300 -100 300 100 100 C\rS\r"
    )
    result = cleanup_payload(_audit_payload(paths))
    assert result.report.to_dict()["summary"]["deleted"] == 0
    assert result.payload.count(b"\rS\r") == 3


def test_alw02_duplicate_requires_identical_paint_and_geometry():
    paths = (
        b"0 0 m\r50 0 L\rS\r1 0 0 1 0 0 0 XA\r0 0 m\r50 0 L\rS\r0 0 m\r50.00001 0 L\rS\r0 0 m\r50 0 L\rs\r"
    )
    result = cleanup_payload(_audit_payload(paths))
    assert result.report.to_dict()["summary"]["deleted"] == 0


def test_alwn2_preserves_shorthand_curves_and_following_strokes():
    for curve in (b"50 80 100 0 v", b"50 80 100 0 y"):
        paths = b"0 0 m\r" + curve + b"\r300 0 L\rS\r0 10 m\r100 10 L\rS\r"
        result = cleanup_payload(_audit_payload(paths))
        assert result.report.to_dict()["summary"]["deleted"] == 0
        assert result.payload.count(b"\rS\r") == 2
        assert b"300 0 L" in result.payload


def test_alw02_preserves_uncertain_path_tail():
    paths = b"0 0 m\runknown_operator\r300 0 L\rS\r"
    result = cleanup_payload(_audit_payload(paths))
    assert paths in result.payload


@pytest.mark.parametrize("command", ["cleanup", "apply-saas"])
@pytest.mark.parametrize("collision", ["report-source", "report-output", "output-source", "report-alias"])
def test_alw01_rejects_colliding_artifacts_before_writes(tmp_path, command, collision):
    src, dst, report = (tmp_path / name for name in ("source.ai", "out.ai", "report.json"))
    _write_native_ai(src, _single_layer_payload())
    original = src.read_bytes()
    if collision == "report-source":
        report = src
    elif collision == "report-output":
        report = dst
    elif collision == "output-source":
        dst = src
    else:
        report.symlink_to(src)
    args = [command, str(src), "-o", str(dst), "--report", str(report)]
    if command == "apply-saas":
        args.append("--architectural")
    result = CliRunner().invoke(cli, args)
    assert result.exit_code != 0
    assert src.read_bytes() == original
    if dst != src:
        assert not dst.exists()


def test_alw01_failed_save_preserves_existing_output(tmp_path, monkeypatch):
    from arch_line_weights.cleanup import cleanup_file

    src, dst = tmp_path / "source.ai", tmp_path / "out.ai"
    _write_native_ai(src, _single_layer_payload())
    dst.write_bytes(b"previous output")

    def broken_save(self, path, **kwargs):
        from pathlib import Path

        Path(path).write_bytes(b"partial")
        raise OSError("synthetic save failure")

    monkeypatch.setattr(pikepdf.Pdf, "save", broken_save)
    with pytest.raises(OSError, match="synthetic"):
        cleanup_file(src, dst)
    assert dst.read_bytes() == b"previous output"


def test_alw17_explicit_progress_file_survives_captured_stderr(tmp_path):
    src, dst, progress = (tmp_path / name for name in ("source.ai", "out.ai", "progress.tsv"))
    _write_native_ai(src, _single_layer_payload())
    result = CliRunner().invoke(
        cli, ["apply-saas", str(src), "--architectural", "-o", str(dst), "--progress-file", str(progress)]
    )
    assert result.exit_code == 0, result.output
    assert progress.exists()
    text = progress.read_text()
    assert "read_payload" in text and "write_payload" in text
    assert "START" in text and "DONE" in text
    assert "START" not in result.stderr
