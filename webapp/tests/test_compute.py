"""Tests for safe schema helpers retained after web processing retirement."""

from __future__ import annotations

from arch_line_weights.apply_saas import ApplySaasResult
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult

from backend.compute import (
    JobStore,
    _apply_to_schema,
    _fills_from_report,
    _poche_to_schema,
    _suggested_output_name,
)
from backend.schemas import JobOptions, JobStatus


def test_apply_summary_round_trip() -> None:
    """ApplySaasResult -> ApplySummary should preserve every counter."""
    result = ApplySaasResult(
        xa_seen=5,
        widths_rewritten=4,
        payload_size_in=100,
        payload_size_out=110,
        chunks_in=1,
        chunks_out=1,
        output_size=200,
        input_size=180,
    )
    s = _apply_to_schema(result)
    assert s.xa_seen == 5
    assert s.widths_rewritten == 4
    assert s.payload_size_in == 100
    assert s.payload_size_out == 110
    assert s.input_size == 180


def test_poche_summary_round_trip() -> None:
    result = PocheSaasResult(
        layers_targeted=3,
        layers_injected=2,
        polygons_injected=4,
        bytes_injected=512,
        layers_missing=["foo::bar"],
    )
    s = _poche_to_schema(result)
    assert s.layers_injected == 2
    assert s.polygons_injected == 4
    assert s.layers_missing == ["foo::bar"]


def test_fills_sorted_by_confidence() -> None:
    """The fills list returned to the API is highest-confidence first."""
    report = PocheReport()
    report.fills = [
        FillResult(layer="A", strategy="rescue", confidence=0.4, polygon_count=1, segment_count=2),
        FillResult(layer="B", strategy="bare", confidence=0.95, polygon_count=2, segment_count=4),
        FillResult(layer="C", strategy="failed", confidence=0.0, polygon_count=0, segment_count=1),
    ]
    rows = _fills_from_report(report)
    assert [r.layer for r in rows] == ["B", "A", "C"]
    assert rows[0].confidence == 0.95


def test_suggested_output_name() -> None:
    assert _suggested_output_name("foo.ai") == "foo HIERARCHY.ai"
    # If user already named it ' HIERARCHY' don't double-append
    assert _suggested_output_name("foo HIERARCHY.ai") == "foo HIERARCHY.ai"
    # Unknown extension defaults to .ai
    assert _suggested_output_name("foo") == "foo HIERARCHY.ai"


def test_job_store_create_and_get() -> None:
    store = JobStore()
    rec = store.create(original_filename="foo.ai", options=JobOptions())
    assert rec.status == JobStatus.PENDING
    fetched = store.get(rec.job_id)
    assert fetched is rec
    assert store.get("nope") is None
