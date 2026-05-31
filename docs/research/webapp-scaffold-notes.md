# Webapp scaffold — design notes (Phase D)

> 2026-04-30. Time-boxed scaffold of the FastAPI + SvelteKit web app that
> wraps the existing `apply_saas` + `poche_saas` pipeline.
> Target: a runnable local skeleton, not a deployment.

## What was built

```
webapp/
├── README.md                       # how to run locally
├── pyproject.toml                  # arch-line-weights-webapp (separate package)
├── backend/
│   ├── main.py                     # FastAPI factory + lifespan
│   ├── config.py                   # ARCHLW_* pydantic-settings
│   ├── schemas.py                  # JobOptions, JobDetail, FillSummary, …
│   ├── storage.py                  # LocalStorage (filesystem stub)
│   ├── compute.py                  # JobStore + run_job (wires apply_saas / poche_saas)
│   └── routes/
│       ├── health.py               # GET /api/health
│       └── jobs.py                 # POST /api/jobs, GET /api/jobs/{id}, /download
├── frontend/                       # SvelteKit + Tailwind (sources only)
│   ├── package.json                # deps; user runs `npm install`
│   ├── svelte.config.js / vite.config.js / tailwind.config.js / postcss.config.js
│   ├── src/
│   │   ├── app.html / app.css / app.d.ts
│   │   ├── lib/api.ts              # typed fetch wrapper
│   │   └── routes/
│   │       ├── +layout.svelte      # header/footer, global stylesheet
│   │       ├── +page.svelte        # drag-drop upload form
│   │       └── jobs/[id]/+page.svelte  # status + poll + download
└── tests/
    ├── conftest.py                 # synthetic-.ai + TestClient fixtures
    ├── test_compute.py             # pipeline glue (7 tests)
    └── test_routes.py              # FastAPI TestClient (8 tests)
```

15 tests. All pass in <0.2 s on the synthetic fixture.

## Key design choices

### 1. `webapp/` is its own pyproject

`webapp/pyproject.toml` declares `arch-line-weights` as a dependency via
`[tool.uv.sources]` (path-editable when developing in this checkout).
Rationale:

- The main package stays free of FastAPI / uvicorn / pydantic-settings deps
  — keeps the CLI install surface lean for users who don't want the webapp
  layer.
- The webapp can iterate on FastAPI versions independently.
- A single `pip install -e webapp/` brings the editable parent in too,
  so there's no two-step dance for contributors.

The `webapp/` package is named `arch-line-weights-webapp` and ships only
the `backend/` directory.

### 2. The runner is a function, not a class

`compute.run_job(record, *, input_path, output_path)` is a plain function
that mutates `record` in place. Three reasons:

1. RQ / Celery task functions look exactly like this. Swapping to a queue
   means `rq.enqueue(run_job, record_id, ...)` — no architectural change.
2. The sync runner inside the route handler can dispatch via
   `starlette.concurrency.run_in_threadpool(run_job, ...)` so the event
   loop stays responsive for concurrent pollers.
3. Tests can call `run_job` directly with `tmp_path` paths — no FastAPI
   layer in the middle, so a regression in the compute glue surfaces in
   `test_compute.py` not buried under HTTP plumbing failures.

### 3. Storage is a separate module with a tiny interface

`backend/storage.py::LocalStorage` exposes `paths_for`, `write_upload`,
`output_size`, `read_output_bytes`, `cleanup_job`. It does not expose
`Path` objects to the route layer except via `JobPaths` (a transparent
dataclass).

This is the only module that touches the filesystem directly. Migrating
to Tigris/R2 means writing an `S3Storage` class with the same interface
and toggling via `ARCHLW_STORAGE_BACKEND`. No route changes.

### 4. In-memory `JobStore` instead of Postgres

A `dict[str, JobRecord]` guarded by a `threading.Lock`. Plenty for the
scaffold; tests get a fresh store per run via
`app.state.job_store = JobStore()` inside the `app_client` fixture.
Production swaps the class for a thin Postgres adapter that exposes the
same `create / get / update` API.

### 5. Synchronous pipeline at request time

`POST /api/jobs` calls `await run_in_threadpool(run_job, ...)` and only
responds once the pipeline has finished. The frontend's poll loop still
works because the response carries `status=done` immediately. When we
move to a queue (Phase D2-D3), the route changes to:

```python
record = store.create(...)
storage.write_upload(...)
queue.enqueue(run_job, record.job_id)
return JobCreated(job_id=record.job_id, status=JobStatus.PENDING)
```

The frontend's polling logic is **already correct for both** — it backs
off and stops on terminal states (`done` or `failed`). No frontend
changes required.

### 6. Frontend uses XHR for upload progress

`fetch()` doesn't expose upload progress events. The `createJob`
function in `lib/api.ts` uses `XMLHttpRequest` so the upload bar in
`+page.svelte` actually moves. Everything else (`getJob`,
`downloadUrl`) uses `fetch`.

### 7. CORS is open to localhost only

The dev defaults are `http://localhost:5173` and `http://127.0.0.1:5173`
(SvelteKit dev server). Production sets `ARCHLW_CORS_ORIGINS` to the
deployed domain.

### 8. Fills sorted by confidence on the server

`compute._fills_from_report` returns `FillSummary` rows sorted
descending by confidence so the frontend can render them naively. The
job-detail page colors confidence cells: ≥0.85 green, >0 amber, =0 red,
mirroring the CLI's `✓ ~ ✗` markers.

## What was skipped (deliberately)

Per task scope:

- No Dockerfile, no `fly.toml`, no GitHub Actions
- No license-key validation (separate task)
- No magic-link auth, no Stripe
- No Redis / RQ wiring (the `job_runner=queue` branch is a stub)
- No retention sweep / file deletion job
- No frontend test framework (Playwright / Vitest)
- No icon library — `+page.svelte` is text-only

The shape is the production shape; only the implementations behind the
`storage.py` and `compute.run_job` boundaries grow.

## Verification

```bash
# Backend
cd webapp
pip install -e .                # pulls editable arch-line-weights from ..
pytest tests/ -q                # 15 tests, all green
cd backend && uvicorn main:app  # serves on :8000
curl localhost:8000/api/health  # {"status":"ok",...}

# Main package still works
cd ../..
pytest tests/ -q                # 202 tests, all green (unchanged)

# Frontend
cd webapp/frontend
npm install                     # one-time, requires internet
npm run dev                     # http://localhost:5173
```

Tested manually:

- `uvicorn backend.main:app` starts cleanly
- `curl /api/health` → 200 with version
- `pytest webapp/tests/` → 15 passed in 0.16 s
- 202 main-package tests unchanged

## Handoff — what's next

1. **Wire Redis + RQ.** Add `redis>=5`, `rq>=1.16` to webapp pyproject.
   Replace the `if settings.job_runner == "sync"` branch with
   `queue.enqueue(run_job, record.job_id, str(input), str(output))`.
   The task function reloads the record from the store and runs the
   same `run_job`. Because `JobStore` is process-local, this also
   requires moving to Postgres-backed job state — see step 2.

2. **Postgres `JobStore`.** Replace the dict with a thin SQLAlchemy or
   `psycopg` wrapper. The `JobRecord` dataclass already maps cleanly
   to a row. Keep the same `create / get / update` surface so the
   route layer doesn't change.

3. **Tigris storage.** Implement `S3Storage` with the same interface
   as `LocalStorage`. Use `boto3` or `aioboto3`. Choose at startup via
   `ARCHLW_STORAGE_BACKEND=tigris` env var.

4. **Magic-link auth.** Resend + Postgres + signed cookie. Wrap the
   POST route in a `Depends(get_current_user)` once it lands.

5. **Stripe metering.** Per Phase D5 — count jobs per user per month,
   gate on the user's plan. The hook lives in `routes/jobs.py::create_job`
   right after `record = store.create(...)`.

6. **Retention sweep.** A cron-like task that walks `storage.root` and
   deletes jobs older than the user's plan limit (7 days free,
   30 days paid). One Fly.io machine on a `fly cron` trigger.

7. **Frontend deploy.** `@sveltejs/adapter-node` instead of
   `adapter-auto`, build into `webapp/frontend/build/`, serve from
   FastAPI static or a separate Fly.io machine.
