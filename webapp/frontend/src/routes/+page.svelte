<script lang="ts">
  import {
    consoleArtifactUrl,
    createConsoleRun,
    runConsoleStage,
    type ConsoleArtifact,
    type ConsoleStage,
    type ConsoleStageKey,
    type ConsoleStatus,
    type ConsoleSummary,
    type ConsoleWorkflow
  } from '$lib/api';
  import ReportBlock from '$lib/ReportBlock.svelte';

  const workflows: { value: ConsoleWorkflow; label: string }[] = [
    { value: 'section', label: 'Section' },
    { value: 'plan', label: 'Plan' },
    { value: 'detail', label: 'Detail' },
    { value: 'synthetic_proof_demo', label: 'Synthetic proof / demo' }
  ];

  const stageDefinitions: { key: ConsoleStageKey; label: string }[] = [
    { key: 'inspect_file', label: 'Inspect File' },
    { key: 'run_layout', label: 'Run Layout' },
    { key: 'apply_line_weights', label: 'Apply Line Weights' },
    { key: 'generate_poche', label: 'Generate Poché' },
    { key: 'export_proof_packet', label: 'Export Proof Packet' }
  ];

  type StageButton = { key: ConsoleStageKey; label: string; status: ConsoleStatus };

  const guardrails = [
    'Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.',
    'Synthetic proof does not close #30.',
    'Private USC regression stays private.'
  ];

  let dragover = false;
  let busy = false;
  let errorMsg = '';
  let chosenFile: File | null = null;
  let workflow: ConsoleWorkflow = 'section';
  let run: ConsoleSummary | null = null;
  let activeStageKey: ConsoleStageKey = 'inspect_file';

  $: selectedStage = run?.stages.find((stage) => stage.key === activeStageKey) ?? stageFor(activeStageKey);
  $: stageButtons = stageDefinitions.map((stage): StageButton => {
    const current = run?.stages.find((candidate) => candidate.key === stage.key);
    return { ...stage, status: current?.status ?? 'not_run' };
  });
  $: canStart = workflow === 'synthetic_proof_demo' || chosenFile !== null;
  $: proofArtifact = run?.artifacts.find((artifact) => artifact.key === 'proof_packet') ?? null;
  $: publicProofLabel =
    run?.posting_clearance === 'GO' ? 'Posting: W5/W7 accepted (local)' : 'Posting: NO-GO';
  $: publicAcceptanceLabel = acceptanceLabel(run);
  $: isSyntheticDemo = (run?.workflow ?? workflow) === 'synthetic_proof_demo';

  function stageFor(key: ConsoleStageKey): ConsoleStage {
    const label = stageDefinitions.find((stage) => stage.key === key)?.label ?? key;
    return {
      key,
      label,
      status: 'not_run',
      what_changed: [],
      what_skipped: [],
      what_failed: [],
      why: [],
      next_step: 'Choose an input file, then run this stage.',
      output_file: null,
      raw_report_available: false,
      updated_at: null
    };
  }

  function resetRun() {
    run = null;
    errorMsg = '';
    activeStageKey = 'inspect_file';
  }

  function onPickFile(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      chosenFile = input.files[0];
      resetRun();
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    dragover = false;
    const f = e.dataTransfer?.files?.[0];
    if (f) {
      chosenFile = f;
      if (workflow === 'synthetic_proof_demo') workflow = 'section';
      resetRun();
    }
  }

  function onWorkflowChange(e: Event) {
    workflow = (e.target as HTMLSelectElement).value as ConsoleWorkflow;
    resetRun();
  }

  async function ensureRun(): Promise<ConsoleSummary> {
    if (run) return run;
    if (!canStart) throw new Error('Choose a .ai or .pdf export first.');
    run = await createConsoleRun(workflow === 'synthetic_proof_demo' ? null : chosenFile, workflow);
    return run;
  }

  async function runStage(stageKey: ConsoleStageKey) {
    activeStageKey = stageKey;
    errorMsg = '';
    busy = true;
    try {
      const current = await ensureRun();
      const optimistic = current.stages.map((stage) =>
        stage.key === stageKey ? { ...stage, status: 'running' as ConsoleStatus } : stage
      );
      run = { ...current, stages: optimistic, overall_status: 'running' };
      run = await runConsoleStage(current.run_id, stageKey);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      busy = false;
    }
  }

  function statusLabel(status: ConsoleStatus): string {
    return status.replace(/_/g, ' ');
  }

  function statusClass(status: ConsoleStatus): string {
    if (status === 'passed') return 'border-emerald-600 bg-emerald-50 text-emerald-800';
    if (status === 'running') return 'border-blue-600 bg-blue-50 text-blue-800';
    if (status === 'needs_review') return 'border-amber-500 bg-amber-50 text-amber-800';
    if (status === 'failed') return 'border-red-600 bg-red-50 text-red-800';
    if (status === 'no_go') return 'border-zinc-950 bg-zinc-950 text-white';
    return 'border-ink-300 bg-white text-ink-500';
  }

  function acceptanceLabel(summary: ConsoleSummary | null): string {
    if (!summary) return 'W5/W7 not recorded';
    if (!summary.public_acceptance?.accepted) return 'W5/W7 not recorded';
    const reviewers = summary.public_acceptance.accepted_by ?? [];
    return reviewers.length ? reviewers.join(', ') : 'Accepted';
  }

  function artifactHref(artifact: ConsoleArtifact): string {
    return consoleArtifactUrl(artifact);
  }
</script>

<section class="space-y-6">
  <header class="flex flex-col gap-3 border-b border-ink-300 pb-5 md:flex-row md:items-end md:justify-between">
    <div class="space-y-1">
      <h1 class="text-2xl font-semibold tracking-tight">Designer Console</h1>
      <p class="max-w-2xl text-sm text-ink-500">
        Local run control for inspection, layout, hierarchy, poché, and proof packet review.
      </p>
    </div>
    {#if run}
      <div class="text-left md:text-right">
        <div class="text-xs uppercase tracking-wide text-ink-500">Overall</div>
        <div class="mt-1 inline-flex rounded border px-2 py-1 text-xs font-semibold {statusClass(run.overall_status)}">
          {statusLabel(run.overall_status)}
        </div>
      </div>
    {/if}
  </header>

  <section class="grid gap-2 md:grid-cols-3">
    {#each run?.guardrails ?? guardrails as notice}
      <div class="border-l-4 border-zinc-950 bg-white px-3 py-2 text-sm font-medium text-ink-900 shadow-sm">
        {notice}
      </div>
    {/each}
  </section>

  {#if isSyntheticDemo}
    <div
      class="border border-amber-500 bg-amber-50 px-4 py-3 text-sm text-amber-950"
      data-testid="synthetic-demo-banner"
    >
      Synthetic proof / demo — exercises the local harness only. It does <strong>not</strong> close
      GitHub issue #30 and is not public posting clearance.
    </div>
  {/if}

  <section class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
    <div class="space-y-4">
      <div
        class="border-2 border-dashed p-8 text-center transition-colors {dragover
          ? 'border-ink-900 bg-white'
          : 'border-ink-300 bg-white'}"
        on:dragenter|preventDefault={() => (dragover = true)}
        on:dragover|preventDefault={() => (dragover = true)}
        on:dragleave={() => (dragover = false)}
        on:drop={onDrop}
        role="button"
        tabindex="0"
      >
        <label class="block cursor-pointer space-y-2">
          <input type="file" accept=".ai,.pdf" class="sr-only" on:change={onPickFile} />
          <span class="block text-base font-medium text-ink-900">
            {chosenFile ? chosenFile.name : 'Choose or drag a Rhino / Illustrator / PDF export'}
          </span>
          <span class="block text-xs text-ink-500">
            {chosenFile
              ? `${(chosenFile.size / 1024 / 1024).toFixed(2)} MB selected`
              : 'Use Synthetic proof / demo when you want a generated local fixture.'}
          </span>
        </label>
      </div>

      <div class="grid gap-3 border border-ink-300 bg-white p-4 md:grid-cols-[220px_minmax(0,1fr)]">
        <label class="space-y-1 text-sm">
          <span class="block font-medium text-ink-700">Workflow type</span>
          <select
            value={workflow}
            on:change={onWorkflowChange}
            data-testid="workflow-select"
            class="w-full rounded border border-ink-300 px-2 py-2"
          >
            {#each workflows as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-5">
          {#each stageButtons as stage}
            <button
              type="button"
              class="min-h-16 border px-3 py-2 text-left text-sm font-semibold transition hover:border-ink-900 disabled:cursor-not-allowed disabled:opacity-45 {activeStageKey ===
              stage.key
                ? 'border-ink-900 bg-ink-900 text-white'
                : 'border-ink-300 bg-white text-ink-900'}"
              data-testid={`stage-${stage.key}`}
              on:click={() => runStage(stage.key)}
              disabled={busy || !canStart}
            >
              <span class="block">{stage.label}</span>
              <span
                class="mt-2 inline-flex rounded border px-1.5 py-0.5 text-[11px] font-medium {statusClass(
                  stage.status
                )}"
              >
                {statusLabel(stage.status)}
              </span>
            </button>
          {/each}
        </div>
      </div>

      {#if errorMsg}
        <div class="border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMsg}
        </div>
      {/if}

      <section class="border border-ink-300 bg-white">
        <div class="border-b border-ink-300 px-4 py-3">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="text-lg font-semibold">{selectedStage.label}</h2>
            <span class="rounded border px-2 py-1 text-xs font-semibold {statusClass(selectedStage.status)}">
              {statusLabel(selectedStage.status)}
            </span>
          </div>
          {#if selectedStage.output_file}
            <p class="mt-1 text-xs text-ink-500">Output: {selectedStage.output_file}</p>
          {/if}
        </div>

        <div class="grid gap-4 p-4 md:grid-cols-2">
          <ReportBlock title="What changed" items={selectedStage.what_changed} empty="Nothing changed yet." />
          <ReportBlock title="What skipped" items={selectedStage.what_skipped} empty="Nothing skipped yet." />
          <ReportBlock title="What failed" items={selectedStage.what_failed} empty="No failures reported." />
          <ReportBlock title="Why" items={selectedStage.why} empty="No explanation yet." />
        </div>

        <div class="border-t border-ink-300 bg-ink-100 px-4 py-3 text-sm">
          <span class="font-semibold text-ink-900">Next step:</span>
          <span class="text-ink-700">{selectedStage.next_step}</span>
        </div>
      </section>
    </div>

    <aside class="space-y-4">
      <section class="border border-ink-300 bg-white">
        <div class="border-b border-ink-300 px-4 py-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-700">Run</h2>
        </div>
        <dl class="space-y-2 px-4 py-3 text-sm">
          <div>
            <dt class="text-ink-500">File</dt>
            <dd class="font-medium text-ink-900">{run?.original_filename ?? chosenFile?.name ?? 'None selected'}</dd>
          </div>
          <div>
            <dt class="text-ink-500">Workflow</dt>
            <dd class="font-medium text-ink-900">
              {run?.workflow_label ?? workflows.find((option) => option.value === workflow)?.label}
            </dd>
          </div>
          <div>
            <dt class="text-ink-500">Public proof</dt>
            <dd>
              <span
                class="inline-flex rounded border px-2 py-1 text-xs font-semibold {run?.public_safe
                  ? statusClass('passed')
                  : statusClass('no_go')}"
              >
                {publicProofLabel}
              </span>
            </dd>
          </div>
          <div>
            <dt class="text-ink-500">Acceptance</dt>
            <dd class="font-medium text-ink-900">{publicAcceptanceLabel}</dd>
          </div>
          <div>
            <dt class="text-ink-500">Run ID</dt>
            <dd class="break-all font-mono text-xs text-ink-700">{run?.run_id ?? 'Not started'}</dd>
          </div>
        </dl>
      </section>

      <section class="border border-ink-300 bg-white">
        <div class="border-b border-ink-300 px-4 py-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-700">Report Rollup</h2>
        </div>
        <div class="space-y-3 px-4 py-3 text-sm">
          <ReportBlock title="Changed" items={run?.report.what_changed ?? []} empty="No changes yet." compact />
          <ReportBlock title="Skipped" items={run?.report.what_skipped ?? []} empty="No skips yet." compact />
          <ReportBlock title="Failed" items={run?.report.what_failed ?? []} empty="No failures yet." compact />
          <ReportBlock title="Why" items={run?.report.why ?? []} empty="No reasons yet." compact />
        </div>
      </section>

      <section class="border border-ink-300 bg-white">
        <div class="border-b border-ink-300 px-4 py-3">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-ink-700">Artifacts</h2>
        </div>
        <div class="space-y-2 px-4 py-3 text-sm">
          {#if proofArtifact}
            <a
              class="inline-flex w-full justify-center rounded bg-ink-900 px-3 py-2 font-medium text-white hover:bg-ink-700"
              href={artifactHref(proofArtifact)}
            >
              Download local review packet
            </a>
          {:else}
            <p class="text-ink-500">No proof packet exported.</p>
          {/if}
          <p class="text-xs text-ink-500">
            {publicProofLabel}. Zip includes <code class="text-[11px]">W5-W7-ACCEPTANCE-HANDOFF.json</code>
            and <code class="text-[11px]">W5-W7-ACCEPTANCE-HANDOFF.md</code> (always NO-GO until W5/W7
            records public acceptance). Raw local reports stay in local storage only.
          </p>
        </div>
      </section>
    </aside>
  </section>
</section>
