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
  public_safe: boolean;
  public_acceptance: PublicAcceptance;
  guardrails: string[];
  proof_notice: string;
}

export interface JobCreated {
  job_id: string;
  status: JobStatus;
  public_safe: boolean;
  public_acceptance: PublicAcceptance;
  guardrails: string[];
  proof_notice: string;
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

export interface PublicAcceptance {
  accepted: boolean;
  accepted_by: string[];
  accepted_at?: string;
  scope?: string;
}

export interface ConsoleSummary {
  schema_version: number;
  run_id: string;
  workflow: ConsoleWorkflow;
  workflow_label: string;
  original_filename: string;
  created_at: string;
  overall_status: ConsoleStatus;
  public_safe: boolean;
  posting_clearance: 'GO' | 'NO-GO';
  synthetic_proof_closes_issue_30: boolean;
  public_acceptance: PublicAcceptance;
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

function processingDisabled(): never {
  throw new Error('Web processing is permanently disabled. Use only documented safe metadata views.');
}

export async function createConsoleRun(
  file: File | null,
  workflow: ConsoleWorkflow
): Promise<ConsoleSummary> {
  return processingDisabled();
}

export async function getConsoleRun(runId: string): Promise<ConsoleSummary> {
  return processingDisabled();
}

export async function runConsoleStage(
  runId: string,
  stageKey: ConsoleStageKey
): Promise<ConsoleSummary> {
  return processingDisabled();
}

export function consoleArtifactUrl(artifact: ConsoleArtifact): string {
  return processingDisabled();
}

/** Retained caller signature; processing is permanently disabled. */
export async function createJob(
  file: File,
  options: Partial<JobOptions> = {},
  onProgress?: (pct: number) => void
): Promise<JobCreated> {
  return processingDisabled();
}

/** GET /api/jobs/{id} — used by the job-detail page's poll loop. */
export async function getJob(jobId: string): Promise<JobDetail> {
  return processingDisabled();
}

/** Resolve a relative download_url onto the backend origin. */
export function downloadUrl(detail: JobDetail): string | null {
  if (!detail.download_url) return null;
  return apiUrl(detail.download_url);
}

