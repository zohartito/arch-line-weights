# arch-line-weights — webapp scaffold (Phase D)

A working FastAPI backend + SvelteKit frontend that wraps the existing pure-Python pipeline (`apply_saas` + `poche_saas`) behind a REST API.

This is a **local skeleton**, not a deployment. It runs against the filesystem, has no auth, no payments, no queue. The shape is meant to be the final shape — production swaps `storage.py` for Tigris/R2 and `compute.run_job` for a Redis+RQ task without changing any other module.

## What's in here

```
webapp/
├── backend/
│   ├── main.py          # FastAPI factory + lifespan
│   ├── routes/
│   │   ├── health.py    # GET /api/health
│   │   └── jobs.py      # POST /api/jobs, GET /api/jobs/{id}, /download
│   ├── compute.py       # Wires apply_saas + poche_saas behind a job runner
│   ├── storage.py       # LocalStorage (filesystem) — swap with S3 later
│   ├── schemas.py       # Pydantic models
│   └── config.py        # ARCHLW_* env-var settings
├── frontend/            # SvelteKit + Tailwind + shadcn-svelte (sources only)
└── tests/
    ├── test_compute.py  # Pipeline glue + run_job E2E
    └── test_routes.py   # FastAPI TestClient on /api/jobs
```

## Run the backend

The webapp depends on the parent `arch-line-weights` package (installed editable from `..`). Install both at once:

```bash
cd webapp
pip install -e .            # editable install pulls in arch-line-weights
pip install -e .[dev]       # add pytest + httpx
```

Run the dev server:

```bash
cd webapp/backend
uvicorn main:app --reload --port 8000
# or from the webapp root:
uvicorn backend.main:app --reload --port 8000
```

Health check:

```bash
curl localhost:8000/api/health
# {"status":"ok","version":"0.0.1","service":"arch-line-weights-webapp"}
```

OpenAPI docs:

- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### Configuration (env vars, all optional)

| Var | Default | Notes |
|---|---|---|
| `ARCHLW_STORAGE_ROOT` | `$TMPDIR/archlw-webapp` | Where uploads + outputs land |
| `ARCHLW_MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Hard cap per upload |
| `ARCHLW_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins |
| `ARCHLW_JOB_RUNNER` | `sync` | `sync` (current) or `queue` (future RQ) |

## Run the tests

```bash
cd webapp
pytest tests/ -q
```

The tests use an isolated `tmp_path` storage per run and a synthetic `.ai` fixture (built via `arch_line_weights.poche_saas.write_synthetic_test_ai`). No real Rhino exports are needed.

## Run the frontend (SvelteKit)

The frontend source files are checked in but **`node_modules` is not pre-populated**. You install yourself:

```bash
cd webapp/frontend
npm install
npm run dev    # http://localhost:5173
```

The frontend talks to the backend at `http://localhost:8000` (configurable via `VITE_API_BASE_URL` in `frontend/.env`).

## REST API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness ping |
| POST | `/api/jobs` | Multipart upload + run pipeline, returns `{job_id, status}` |
| GET | `/api/jobs/{id}` | Status + (when DONE) `download_url` + per-layer poché report |
| GET | `/api/jobs/{id}/download` | Stream the processed file |

POST `/api/jobs` form fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | multipart | (required) | `.ai` or `.pdf` |
| `preset` | str | `section` | One of the registered preset names |
| `scale` | str | `1/4` | ISO 128 scale |
| `for_print` | bool | `false` | Use ISO-128 print weights |
| `with_poche` | bool | `true` | Inject black fills into cut layers |
| `default_width` | float | `0.25` | Width applied to unmatched colors |

## What this is not (yet)

- No magic-link auth — anonymous access only
- No Stripe / billing — every job is free
- No retention sweep — local files persist until you delete them
- No Dockerfile / fly.toml — `pip install + uvicorn` is the deploy story for now
- No license-key validation — that lives in a separate task
- No queue — `job_runner=sync` blocks the request until done

The split between `storage.py` and `compute.py` is the only thing that needs to grow when those land. Everything else is shape-correct already.

## Design notes

See `docs/research/webapp-scaffold-notes.md` for the design decisions, what was deferred, and handoff notes for the next iteration.
