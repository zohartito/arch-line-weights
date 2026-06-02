from __future__ import annotations

import json

import pikepdf
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
