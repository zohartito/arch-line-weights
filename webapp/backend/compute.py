"""Compute glue — wires apply_saas + poche_saas behind a job runner.

This module deliberately holds NO algorithm. All real work lives in
``arch_line_weights.apply_saas`` and ``arch_line_weights.poche_saas``; we
just pick the entry point based on ``JobOptions.with_poche``, run it, and
package the result into the API schema.

The "runner" abstraction is a thin function that takes a ``JobRecord`` and
mutates it. The current scaffold runs synchronously inside the request
handler (good enough for local + tests). Swapping to RQ/Celery means:
   1. ``run_job`` becomes a queue-task entry point
   2. ``JobStore.create`` enqueues the task
   3. The status updates flow through Postgres rather than a process-local dict
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arch_line_weights.classify import auto_by_luminance, from_user_mapping
from arch_line_weights.inspect import inspect_file
from arch_line_weights.presets import select_preset

from .schemas import (
    ApplySummary,
    FillSummary,
    JobDetail,
    JobOptions,
    JobStatus,
    PocheSummary,
)

logger = logging.getLogger("archlw.webapp")


@dataclass
class JobRecord:
    """In-memory job state. Production replaces this with a Postgres row.

    The split between ``JobRecord`` (mutable, server-internal) and ``JobDetail``
    (immutable response model) lets us evolve internal storage without leaking
    a Pydantic model into the queue task.
    """

    job_id: str
    original_filename: str
    options: JobOptions
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    apply_summary: ApplySummary | None = None
    poche_summary: PocheSummary | None = None
    fills: list[FillSummary] = field(default_factory=list)
    flags_applied: dict[str, Any] = field(default_factory=dict)
    output_filename: str | None = None
    error: str | None = None

    def to_detail(self, *, download_url: str | None) -> JobDetail:
        return JobDetail(
            job_id=self.job_id,
            status=self.status,
            created_at=self.created_at,
            finished_at=self.finished_at,
            original_filename=self.original_filename,
            options=self.options,
            apply_summary=self.apply_summary,
            poche_summary=self.poche_summary,
            fills=list(self.fills),
            flags_applied=dict(self.flags_applied),
            download_url=download_url,
            error=self.error,
        )


class JobStore:
    """Process-local thread-safe job table. Swap for Postgres in production.

    A single instance is created at app startup and held on
    ``app.state.job_store``. Routes pull it via the ``get_job_store`` dep so
    tests can inject a fresh store per run.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex

    def create(self, *, original_filename: str, options: JobOptions) -> JobRecord:
        record = JobRecord(
            job_id=self.new_id(),
            original_filename=original_filename,
            options=options,
        )
        with self._lock:
            self._jobs[record.job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> list[JobRecord]:
        with self._lock:
            return list(self._jobs.values())

    def update(self, record: JobRecord) -> None:
        with self._lock:
            self._jobs[record.job_id] = record


def run_job(
    record: JobRecord,
    *,
    input_path: Path,
    output_path: Path,
) -> JobRecord:
    """Run the full pipeline for one job, mutating ``record`` in place.

    1. Inspect the file to get the color → frequency table.
    2. Build an auto-by-luminance mapping using the requested preset/scale.
    3. Run apply_saas (or apply_saas_with_poche when ``with_poche=True``).
    4. Convert dataclass results into Pydantic schema rows.

    Errors are caught, stored on the record, and re-raised — the caller
    decides whether to surface or swallow. Sync runner uses the in-place
    record; queue runner re-fetches from the store.
    """
    record.status = JobStatus.RUNNING
    record.flags_applied = _flags_snapshot(record.options)
    logger.info(
        "job %s starting: file=%s flags=%s",
        record.job_id,
        record.original_filename,
        record.flags_applied,
    )
    try:
        rep = inspect_file(str(input_path))
        tiers = select_preset(
            record.options.preset,
            scale=record.options.scale,
            for_print=record.options.for_print,
        )
        mapping = auto_by_luminance(rep, tiers)
        mapping = from_user_mapping(mapping)

        if record.options.with_poche:
            from arch_line_weights.poche_saas import apply_saas_with_poche

            # `--llm-fallback` is gated on ARCH_LW_LLM_FALLBACK at the
            # ``llm_topology`` import site; we set it for the duration of the
            # call and restore it afterwards so cross-job state never leaks.
            # The CLI sets the same env var globally; for the webapp we keep
            # the lifetime to one job to allow concurrent jobs with different
            # flag values once the queue runner lands.
            with _llm_fallback_env(record.options.llm_fallback):
                apply_result, poche_result, poche_report = apply_saas_with_poche(
                    str(input_path),
                    str(output_path),
                    mapping,
                    default_width=record.options.default_width,
                    use_alpha_shape=record.options.alpha_shape,
                    bridge_strategy=record.options.bridge_strategy,
                )
            record.apply_summary = _apply_to_schema(apply_result)
            record.poche_summary = _poche_to_schema(poche_result)
            record.fills = _fills_from_report(poche_report)
        else:
            from arch_line_weights.apply_saas import apply_to_file as apply_to_file_saas

            apply_result = apply_to_file_saas(
                str(input_path),
                str(output_path),
                mapping,
                default_width=record.options.default_width,
            )
            record.apply_summary = _apply_to_schema(apply_result)

        record.output_filename = _suggested_output_name(record.original_filename)
        record.status = JobStatus.DONE
        logger.info(
            "job %s done: applied flags=%s",
            record.job_id,
            record.flags_applied,
        )
    except Exception as exc:  # noqa: BLE001 — we want the message in the API
        record.error = f"{type(exc).__name__}: {exc}"
        record.status = JobStatus.FAILED
        logger.exception("job %s failed", record.job_id)
        # Do not re-raise — keep the API contract clean. The frontend reads
        # `status=failed` + `error` and surfaces both.
    finally:
        record.finished_at = datetime.now(timezone.utc)
    return record


# --------------------------------------------------------------------------- #
# Helpers — convert dataclasses to API schemas
# --------------------------------------------------------------------------- #


def _flags_snapshot(options: JobOptions) -> dict[str, Any]:
    """Snapshot the resolved per-job flag set for logging and the API echo.

    Returns the same shape the CLI documents in ``--help``: each user-facing
    knob and its effective value. The frontend renders this verbatim so
    operators can confirm what the pipeline actually saw (vs the form
    defaults the browser silently filled in).
    """
    return {
        "preset": options.preset,
        "scale": options.scale,
        "for_print": options.for_print,
        "with_poche": options.with_poche,
        "default_width": options.default_width,
        "bridge_strategy": options.bridge_strategy,
        "alpha_shape": options.alpha_shape,
        "llm_fallback": options.llm_fallback,
        "source": options.source,
    }


class _llm_fallback_env:  # noqa: N801 — context-manager naming convention
    """Scoped toggle for ``ARCH_LW_LLM_FALLBACK``.

    The CLI sets the env var globally for the run; the webapp scopes it to
    a single job so concurrent jobs (once we move off the sync runner) can
    use different ``llm_fallback`` settings without stepping on each other.

    Restores any previous value on exit, even if the wrapped pipeline
    raises — leaving the env var dirty across requests would silently
    enable the LLM rung for jobs that didn't ask for it.
    """

    _ENV_VAR = "ARCH_LW_LLM_FALLBACK"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._prior: str | None = None
        self._was_set = False

    def __enter__(self) -> "_llm_fallback_env":
        self._was_set = self._ENV_VAR in os.environ
        self._prior = os.environ.get(self._ENV_VAR)
        if self.enabled:
            os.environ[self._ENV_VAR] = "1"
        elif self._was_set:
            # Caller asked for LLM off but the env had it on — clear it for
            # this job so the rung doesn't fire.
            os.environ.pop(self._ENV_VAR, None)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._was_set:
            assert self._prior is not None  # guaranteed by _was_set
            os.environ[self._ENV_VAR] = self._prior
        else:
            os.environ.pop(self._ENV_VAR, None)


def _apply_to_schema(result) -> ApplySummary:
    """Map :class:`apply_saas.ApplySaasResult` -> :class:`ApplySummary`."""
    d = asdict(result)
    return ApplySummary(
        xa_seen=d["xa_seen"],
        widths_rewritten=d["widths_rewritten"],
        payload_size_in=d["payload_size_in"],
        payload_size_out=d["payload_size_out"],
        chunks_in=d["chunks_in"],
        chunks_out=d["chunks_out"],
        output_size=d["output_size"],
        input_size=d["input_size"],
    )


def _poche_to_schema(result) -> PocheSummary:
    """Map :class:`poche_saas.PocheSaasResult` -> :class:`PocheSummary`."""
    return PocheSummary(
        layers_targeted=result.layers_targeted,
        layers_injected=result.layers_injected,
        polygons_injected=result.polygons_injected,
        bytes_injected=result.bytes_injected,
        layers_missing=list(result.layers_missing),
    )


def _fills_from_report(report) -> list[FillSummary]:
    """Map :class:`poche.PocheReport.fills` -> [FillSummary, ...]."""
    out: list[FillSummary] = []
    for fr in report.fills:
        out.append(
            FillSummary(
                layer=fr.layer,
                strategy=str(fr.strategy),
                confidence=float(fr.confidence),
                polygon_count=int(fr.polygon_count),
                segment_count=int(fr.segment_count),
            )
        )
    out.sort(key=lambda f: -f.confidence)
    return out


def _suggested_output_name(original: str) -> str:
    """Append ' HIERARCHY' to the stem, mirroring the CLI's default output naming."""
    p = Path(original)
    stem = p.stem
    if " HIERARCHY" not in stem:
        stem = f"{stem} HIERARCHY"
    return f"{stem}{p.suffix or '.ai'}"
