"""Tests for the compute module — verify the schema-mapping helpers and
end-to-end ``run_job`` against the synthetic fixture.

These tests deliberately avoid the FastAPI layer so a regression in the
compute glue surfaces here, not buried under HTTP plumbing failures.
"""

from __future__ import annotations

from pathlib import Path

from arch_line_weights.apply_saas import ApplySaasResult
from arch_line_weights.poche import FillResult, PocheReport
from arch_line_weights.poche_saas import PocheSaasResult

from backend.compute import (
    JobRecord,
    JobStore,
    _apply_to_schema,
    _fills_from_report,
    _poche_to_schema,
    _suggested_output_name,
    run_job,
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


def test_run_job_end_to_end(synthetic_ai: Path, tmp_path: Path) -> None:
    """Run the full pipeline against the synthetic .ai and inspect the record."""
    output_path = tmp_path / "output.ai"
    record = JobRecord(
        job_id="test-job-1",
        original_filename=synthetic_ai.name,
        options=JobOptions(with_poche=True),
    )
    run_job(record, input_path=synthetic_ai, output_path=output_path)

    assert record.status == JobStatus.DONE, record.error
    assert output_path.exists()
    assert record.apply_summary is not None
    assert record.poche_summary is not None
    # The synthetic fixture has one cut layer, so we should see at least
    # one fill row and a sane polygon count (>=1 from the unit square).
    assert record.poche_summary.layers_targeted >= 1
    # `fills` is sorted by confidence desc so we can trust [0] is the best.
    assert len(record.fills) >= 1


def test_run_job_handles_missing_input(tmp_path: Path) -> None:
    """A bad input path should put the job in FAILED, not raise."""
    record = JobRecord(
        job_id="test-job-2",
        original_filename="missing.ai",
        options=JobOptions(with_poche=False),
    )
    run_job(
        record,
        input_path=tmp_path / "nope.ai",
        output_path=tmp_path / "out.ai",
    )
    assert record.status == JobStatus.FAILED
    assert record.error is not None


def test_job_store_create_and_get() -> None:
    store = JobStore()
    rec = store.create(original_filename="foo.ai", options=JobOptions())
    assert rec.status == JobStatus.PENDING
    fetched = store.get(rec.job_id)
    assert fetched is rec
    assert store.get("nope") is None
