"""Job routes — POST /api/jobs (upload + process) and GET /api/jobs/{id}.

The current scaffold runs the pipeline synchronously inside the POST handler
because the compute (10–60 s) is short enough to survive a normal HTTP
timeout when the frontend extends to 120 s, and the in-memory job store
makes async hand-off awkward to test. The next iteration moves the call
inside ``run_job`` to a background task / queue without changing the API
shape — clients already poll, so they won't notice.
"""

from __future__ import annotations

from pathlib import Path

import hmac
import ipaddress

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from arch_line_weights.input_format import diagnostic_for_command

from ..compute import JobStore, run_job
from ..config import Settings, get_settings
from ..schemas import JobCreated, JobDetail, JobOptions, JobStatus
from ..storage import LocalStorage

router = APIRouter(prefix="/api", tags=["jobs"])


def require_local_capability(
    request: Request,
    settings: Settings = Depends(get_settings),
    origin: str | None = Header(None),
    capability: str | None = Header(None, alias="X-Archlw-Capability"),
) -> None:
    """Require an exact launcher origin and a per-launch local capability.

    The legacy job API is intentionally fail-closed when a launcher has not
    provisioned a capability; loopback binding alone is not an authorization
    boundary for browser-controlled requests.
    """
    expected = settings.local_api_capability
    client_host = request.client.host if request.client else ""
    try:
        is_loopback = ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        is_loopback = False
    if not expected or not is_loopback or origin not in settings.cors_origins:
        raise HTTPException(status_code=403, detail="local job capability required")
    if not capability or not hmac.compare_digest(capability, expected):
        raise HTTPException(status_code=403, detail="local job capability required")


def get_job_store(request: Request) -> JobStore:
    """Pull the job store off ``app.state``. Tests override this dep."""
    return request.app.state.job_store


def get_storage(request: Request) -> LocalStorage:
    """Pull the storage backend off ``app.state``. Tests override this dep."""
    return request.app.state.storage


# --------------------------------------------------------------------------- #
# Upload + run
# --------------------------------------------------------------------------- #


@router.post("/jobs", response_model=JobCreated)
async def create_job(
    file: UploadFile = File(...),
    # Core flags (v0.4 baseline)
    preset: str = Form("section"),
    scale: str = Form("1/4"),
    for_print: bool = Form(False),
    with_poche: bool = Form(True),
    default_width: float = Form(0.25),
    # v0.5+ / v0.6.x flags. Defaults track the CLI defaults so callers that
    # don't know about them get the same behaviour as `arch-lw apply-saas`.
    bridge_strategy: str = Form("best"),
    alpha_shape: bool = Form(True),
    llm_fallback: bool = Form(False),
    source: str = Form("auto"),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
    storage: LocalStorage = Depends(get_storage),
    _capability: None = Depends(require_local_capability),
) -> JobCreated:
    """Accept a multipart upload, store it, run the pipeline, return the job id.

    The route mounts the upload onto disk first (so the pipeline can mmap-style
    open it via pikepdf), then dispatches based on ``settings.job_runner``.
    The "sync" runner blocks the request until done; "queue" enqueues and
    returns ``status=PENDING`` immediately.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="upload missing a filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".ai", ".pdf"):
        raise HTTPException(
            status_code=415,
            detail=f"unsupported file type {suffix!r}; expected .ai or .pdf",
        )

    # Build the options through Pydantic so any out-of-vocabulary enum
    # value (e.g. preset="bogus") returns a 422 with the validation
    # detail attached, matching FastAPI's native body-validation behaviour.
    try:
        options = JobOptions(
            preset=preset,
            scale=scale,
            for_print=for_print,
            with_poche=with_poche,
            default_width=default_width,
            bridge_strategy=bridge_strategy,
            alpha_shape=alpha_shape,
            llm_fallback=llm_fallback,
            source=source,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    record = store.create(original_filename=file.filename, options=options)

    # Stream the upload to disk. We bound size at the configured cap so a
    # rogue client can't flood the volume; FastAPI streams body in chunks.
    try:
        paths = storage.write_upload(
            record.job_id, file.file, filename=file.filename, max_bytes=settings.max_upload_bytes
        )
    except ValueError as exc:
        storage.cleanup_job(record.job_id)
        raise HTTPException(
            status_code=413,
            detail="upload exceeds configured byte limit",
        ) from exc

    input_diag = diagnostic_for_command(paths.input_path, "apply-saas")
    if not input_diag.command_support["apply-saas"]:
        storage.cleanup_job(record.job_id)
        raise HTTPException(
            status_code=415,
            detail={
                "message": input_diag.unsupported_reason,
                "suggested_next_step": input_diag.suggested_next_step,
                "input_format": input_diag.to_dict(),
            },
        )

    # Run synchronously in a threadpool so the event loop stays responsive
    # for any concurrent /api/jobs/{id} pollers. ``run_job`` mutates ``record``
    # in place so callers see updated status without re-fetching.
    if settings.job_runner == "sync":
        await run_in_threadpool(
            run_job,
            record,
            input_path=paths.input_path,
            output_path=paths.output_path,
        )
        store.update(record)
    else:  # pragma: no cover — queue path arrives in a later phase
        # In production, enqueue an RQ task: rq.enqueue(run_job, record_id, ...)
        # For now we just leave PENDING; tests don't exercise this branch.
        pass

    return JobCreated(job_id=record.job_id, status=record.status)


# --------------------------------------------------------------------------- #
# Status / detail
# --------------------------------------------------------------------------- #


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(
    job_id: str,
    request: Request,
    store: JobStore = Depends(get_job_store),
    storage: LocalStorage = Depends(get_storage),
    _capability: None = Depends(require_local_capability),
) -> JobDetail:
    """Status + (when DONE) a download URL.

    The download URL is built relative to the request so the frontend can
    use it as-is regardless of host. We do NOT include the absolute output
    path — clients only need the URL and the size.
    """
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown job_id")

    download_url: str | None = None
    if record.status == JobStatus.DONE and storage.output_size(record.job_id):
        # request.url_for produces a fully-qualified URL; we emit a
        # path-only value so the frontend can prepend its own origin if it
        # wants to keep the response cacheable across environments.
        download_url = str(request.url_for("download_job", job_id=record.job_id).path)

    return record.to_detail(download_url=download_url)


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #


@router.get("/jobs/{job_id}/download", name="download_job")
def download_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    storage: LocalStorage = Depends(get_storage),
    _capability: None = Depends(require_local_capability),
) -> FileResponse:
    """Stream the processed file. 404 if unknown, 409 if not yet DONE."""
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    if record.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail=f"job is {record.status.value}, not done")

    paths = storage.paths_for(job_id)
    if not paths.output_path.exists():
        raise HTTPException(status_code=404, detail="output missing on disk")

    suggested = record.output_filename or paths.output_path.name
    return FileResponse(
        path=paths.output_path,
        filename=suggested,
        media_type="application/postscript",
    )
