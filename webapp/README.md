# arch-line-weights — webapp scaffold (Phase D)

> **Experimental/local only.** This scaffold is not the public Day-1 install
> path and is not hardened SaaS. The supported dogfood path is the local CLI,
> especially `arch-lw apply-saas --architectural --poche` for submit-quality
> board output.

A working FastAPI backend + SvelteKit frontend that wraps the existing arch-line-weights pipeline behind a REST API.

The current first screen is the **local designer console prototype**. It is a
quiet workstation tool for selecting a Rhino / Illustrator / PDF export,
running staged checks, reading a report, and exporting a local proof packet.
It is not posting clearance and not desktop packaging.

This is a **local skeleton**, not a deployment. It runs against the filesystem, has no auth, no payments, no queue. The shape is meant to be the final shape — production swaps `storage.py` for Tigris/R2 and `compute.run_job` for a Redis+RQ task without changing any other module.

## What's in here

```
webapp/
├── backend/
│   ├── main.py          # FastAPI factory + lifespan
│   ├── routes/
│   │   ├── health.py    # GET /api/health
│   │   ├── jobs.py      # Legacy one-shot POST /api/jobs flow
│   │   └── console.py   # Designer console staged workflow API
│   ├── compute.py       # Wires apply_saas + poche_saas behind a job runner
│   ├── console.py       # Local console run state, stages, proof packet export
│   ├── storage.py       # LocalStorage (filesystem) — swap with S3 later
│   ├── schemas.py       # Pydantic models
│   └── config.py        # ARCHLW_* env-var settings
├── frontend/            # SvelteKit + Tailwind + shadcn-svelte (sources only)
└── tests/
    ├── test_compute.py  # Pipeline glue + run_job E2E
    └── test_routes.py   # FastAPI TestClient on /api/jobs
```

## Open the Designer Console

Install once, then use the one-command launcher:

```bash
cd webapp
pip install -e .. -e '.[dev]'
cd frontend
npm install
```

```bash
cd webapp
arch-lw-web-console
```

The launcher starts FastAPI and SvelteKit together, chooses open local ports,
sets the frontend API URL, prints the console URL, and opens it in your browser.
Use `arch-lw-web-console --no-open` when running automated smoke checks.

Manual two-terminal launch is still available for debugging. The frontend talks
to the backend at `http://localhost:8000` by default (`VITE_API_BASE_URL` can
override it). If Vite shifts to `5174`, `5175`, or another nearby local dev
port because `5173` is occupied, use the printed URL; the backend allows the
local Vite fallback ports by default.

### What it can do

- Choose or drag a `.ai` / `.pdf` export.
- Choose workflow type: Section, Plan, Detail, or Synthetic proof / demo.
- Run explicit actions: Inspect File, Run Layout, Apply Line Weights, Generate
  Poché, Export Proof Packet.
- Show each stage as `not_run`, `running`, `passed`, `needs_review`, `failed`,
  or `no_go`.
- Show a readable report: what changed, what skipped, what failed, why, and the
  next step.
- Keep raw local reports under the local storage root while local review packets
  only include sanitized summaries plus a redacted W5/W7 acceptance handoff
  template.
- Mark proof summaries as `public_safe: false` until explicit W5/W7 acceptance
  is recorded by a future acceptance workflow.

### What it cannot claim

The console always shows these guardrails:

- Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.
- Synthetic proof does not close #30.
- Private USC regression stays private.

This prototype does not close #29 or #30. It does not mean public launch is
ready. It does not mean App Store, Microsoft Store, or Windows desktop support
is ready. Windows remains future work until it is packaged and tested on
Windows. Exported proof packets are local review packets, not posting clearance.
They include `public-summary.json`, `README-NOT-PUBLIC-CLEARANCE.txt`, and
W5/W7 handoff templates for recording a redacted accept/reject decision while
keeping private review inputs local.

### Roadmap

1. Local web prototype: keep improving the FastAPI + SvelteKit console around
   the existing engine and report contracts.
2. Signed Mac desktop beta: package the same local console/engine with signing,
   notarization, update notes, and a tested local-file permission story.
3. Windows desktop beta: package and test on Windows before making any Windows
   support claim.
4. Rhino plugin / Illustrator panel: later, wrap the same staged workflow inside
   native design-tool surfaces once the local console proves the workflow.

## Run the backend directly

The webapp depends on the parent `arch-line-weights` package. Install both local
packages at once:

```bash
cd webapp
pip install -e .. -e .        # parent engine + webapp
pip install -e .. -e '.[dev]' # add pytest + httpx + ruff
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
| `ARCHLW_CORS_ORIGINS` | local Vite ports `5173`-`5179` on `localhost` and `127.0.0.1` | Comma-separated browser origins |
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
npm run dev    # open the Local URL Vite prints
```

The frontend talks to the backend at `http://localhost:8000` (configurable via `VITE_API_BASE_URL` in `frontend/.env`).

## One-command local console launcher

After the editable install and frontend dependency install above, this starts
both local servers:

```bash
cd webapp
arch-lw-web-console
```

Useful flags:

| Flag | Purpose |
|---|---|
| `--no-open` | Print the URL without opening a browser |
| `--backend-port 8010` | Start searching for the backend port at 8010 |
| `--frontend-port 5174` | Start searching for the frontend port at 5174 |
| `--storage-root /path/to/local-output` | Put local run files under a chosen folder |
| `--reload` | Start FastAPI with `uvicorn --reload` |

The command keeps raw local reports in local storage. It is a prototype launch
helper, not desktop packaging.

## REST API

Designer console:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/console/guardrails` | Local no-go notices |
| POST | `/api/console/runs` | Create a console run from upload or synthetic demo |
| GET | `/api/console/runs/{id}` | Public-safe run summary |
| POST | `/api/console/runs/{id}/stages/{stage}` | Run one console action |
| GET | `/api/console/runs/{id}/artifacts/{key}` | Download proof packet artifact |

Legacy one-shot job flow:

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
| `preset` | enum | `section` | One of `section`, `plan`, `elevation`, `detail` |
| `scale` | enum | `1/4` | One of `1/16`, `1/8`, `1/4`, `1/2`, `1`, `3`, `full` |
| `for_print` | bool | `false` | Use ISO-128 print weights at the chosen scale |
| `with_poche` | bool | `true` | Inject black fills into cut layers |
| `default_width` | float | `0.25` | Width applied to unmatched colors |
| `bridge_strategy` | enum | `best` | `greedy` (v0.4 nearest-neighbour) or `best` (try 4, pick highest-yield) |
| `alpha_shape` | bool | `true` | α-shape rescue rung between auto_bridge and concave_hull |
| `llm_fallback` | bool | `false` | Opt-in LLM topology rescue (rung 5). Requires `ANTHROPIC_API_KEY` |
| `source` | enum | `auto` | `auto`, `rhino`, or `autocad` (forces a layer-name convention) |

Unknown enum values return **422** with the Pydantic validation error
attached. Unknown booleans coerce per FastAPI's standard form handling.

`GET /api/jobs/{id}` includes a `flags_applied` dict echoing the resolved
options (useful for confirming the pipeline saw what the form sent), plus
`poche_summary` + `fills` when `with_poche=true`.

Example: run with every v0.6.x flag explicit.

```bash
curl -X POST http://localhost:8000/api/jobs \
  -F "file=@drawing.ai" \
  -F "preset=section" \
  -F "scale=1/4" \
  -F "for_print=false" \
  -F "with_poche=true" \
  -F "default_width=0.25" \
  -F "bridge_strategy=best" \
  -F "alpha_shape=true" \
  -F "llm_fallback=false" \
  -F "source=auto"
```

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
