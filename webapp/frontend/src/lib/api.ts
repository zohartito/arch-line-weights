// Tiny fetch wrapper around the FastAPI backend.
//
// We deliberately keep this single-file and dependency-free — there's no
// codegen, no SDK; just typed shapes that mirror the Pydantic models on
// the backend. When the API surface grows we'll regenerate from OpenAPI
// (FastAPI exposes `/openapi.json`), but for the scaffold this is leaner
// and easier to read.

const API_BASE_URL =
  // Vite injects env vars at build time; falling back to localhost lets the
  // frontend Just Work in dev without a .env.
  (import.meta as unknown as { env: Record<string, string> }).env
    ?.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type JobStatus = 'pending' | 'running' | 'done' | 'failed';
export type ConsoleStatus = 'not_run' | 'running' | 'passed' | 'needs_review' | 'failed' | 'no_go';
export type ConsoleWorkflow = 'section' | 'plan' | 'detail' | 'synthetic_proof_demo';
export type ConsoleStageKey =
  | 'inspect_file'
  | 'run_layout'
  | 'apply_line_weights'
  | 'generate_poche'
  | 'export_proof_packet';

export interface JobOptions {
  preset: string;
  scale: string;
  for_print: boolean;
  with_poche: boolean;
  default_width: number;
}

export interface ApplySummary {
  xa_seen: number;
  widths_rewritten: number;
  payload_size_in: number;
  payload_size_out: number;
  chunks_in: number;
  chunks_out: number;
  output_size: number;
  input_size: number;
}

export interface PocheSummary {
  layers_targeted: number;
  layers_injected: number;
  polygons_injected: number;
  bytes_injected: number;
  layers_missing: string[];
}

export interface FillSummary {
  layer: string;
  strategy: string;
  confidence: number;
  polygon_count: number;
  segment_count: number;
}

export interface JobDetail {
  job_id: string;
  status: JobStatus;
  created_at: string;
  finished_at: string | null;
  original_filename: string;
  options: JobOptions;
  apply_summary: ApplySummary | null;
  poche_summary: PocheSummary | null;
  fills: FillSummary[];
  download_url: string | null;
  error: string | null;
}

export interface JobCreated {
  job_id: string;
  status: JobStatus;
}

export interface ConsoleStage {
  key: ConsoleStageKey;
  label: string;
  status: ConsoleStatus;
  what_changed: string[];
  what_skipped: string[];
  what_failed: string[];
  why: string[];
  next_step: string;
  output_file: string | null;
  raw_report_available: boolean;
  updated_at: string | null;
}

export interface ConsoleArtifact {
  key: string;
  filename: string;
  available: boolean;
  download_url: string;
}

export interface ConsoleReport {
  what_changed: string[];
  what_skipped: string[];
  what_failed: string[];
  why: string[];
  next_step: string;
}

export interface ConsoleSummary {
  schema_version: number;
  run_id: string;
  workflow: ConsoleWorkflow;
  workflow_label: string;
  original_filename: string;
  created_at: string;
  overall_status: ConsoleStatus;
  guardrails: string[];
  stages: ConsoleStage[];
  report: ConsoleReport;
  artifacts: ConsoleArtifact[];
}

/** Build an absolute URL pointing at the backend, joining the path
 *  cleanly regardless of whether the base ends in `/`. */
export function apiUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${base}${suffix}`;
}

export async function createConsoleRun(
  file: File | null,
  workflow: ConsoleWorkflow
): Promise<ConsoleSummary> {
  const form = new FormData();
  form.append('workflow', workflow);
  if (file) form.append('file', file);
  const resp = await fetch(apiUrl('/api/console/runs'), {
    method: 'POST',
    body: form
  });
  if (!resp.ok) {
    const body = await safeJson(resp);
    throw new Error(readDetail(body?.detail) ?? `HTTP ${resp.status}`);
  }
  return (await resp.json()) as ConsoleSummary;
}

export async function getConsoleRun(runId: string): Promise<ConsoleSummary> {
  const resp = await fetch(apiUrl(`/api/console/runs/${encodeURIComponent(runId)}`));
  if (!resp.ok) {
    const body = await safeJson(resp);
    throw new Error(readDetail(body?.detail) ?? `HTTP ${resp.status}`);
  }
  return (await resp.json()) as ConsoleSummary;
}

export async function runConsoleStage(
  runId: string,
  stageKey: ConsoleStageKey
): Promise<ConsoleSummary> {
  const resp = await fetch(
    apiUrl(`/api/console/runs/${encodeURIComponent(runId)}/stages/${stageKey}`),
    { method: 'POST' }
  );
  if (!resp.ok) {
    const body = await safeJson(resp);
    throw new Error(readDetail(body?.detail) ?? `HTTP ${resp.status}`);
  }
  return (await resp.json()) as ConsoleSummary;
}

export function consoleArtifactUrl(artifact: ConsoleArtifact): string {
  return apiUrl(artifact.download_url);
}

/** POST /api/jobs — multipart upload + run. Optional progress callback
 *  is wired for completeness; the FastAPI route currently runs sync so
 *  upload progress is the only place a percentage is meaningful. */
export async function createJob(
  file: File,
  options: Partial<JobOptions> = {},
  onProgress?: (pct: number) => void
): Promise<JobCreated> {
  const form = new FormData();
  form.append('file', file);
  form.append('preset', options.preset ?? 'section');
  form.append('scale', options.scale ?? '1/4');
  form.append('for_print', String(options.for_print ?? false));
  form.append('with_poche', String(options.with_poche ?? true));
  form.append('default_width', String(options.default_width ?? 0.25));

  // We use XMLHttpRequest for upload progress (fetch doesn't expose it).
  return new Promise<JobCreated>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', apiUrl('/api/jobs'));
    xhr.responseType = 'json';
    xhr.upload.onprogress = (e) => {
      if (onProgress && e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as JobCreated);
      } else {
        const detail =
          xhr.response && typeof xhr.response === 'object' && 'detail' in xhr.response
            ? (xhr.response as { detail?: string }).detail
            : `HTTP ${xhr.status}`;
        reject(new Error(detail ?? `HTTP ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error('network error'));
    xhr.send(form);
  });
}

/** GET /api/jobs/{id} — used by the job-detail page's poll loop. */
export async function getJob(jobId: string): Promise<JobDetail> {
  const resp = await fetch(apiUrl(`/api/jobs/${encodeURIComponent(jobId)}`));
  if (!resp.ok) {
    const body = await safeJson(resp);
    throw new Error(readDetail(body?.detail) ?? `HTTP ${resp.status}`);
  }
  return (await resp.json()) as JobDetail;
}

/** Resolve a relative download_url onto the backend origin. */
export function downloadUrl(detail: JobDetail): string | null {
  if (!detail.download_url) return null;
  return apiUrl(detail.download_url);
}

async function safeJson(resp: Response): Promise<{ detail?: unknown } | null> {
  try {
    return (await resp.json()) as { detail?: unknown };
  } catch {
    return null;
  }
}

function readDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => JSON.stringify(item)).join('; ');
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return null;
}
