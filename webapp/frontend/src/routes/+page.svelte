<script lang="ts">
  import { goto } from '$app/navigation';
  import { createJob, type JobOptions } from '$lib/api';

  // Local component state. Svelte 4 reactive `let`s are enough for this
  // form — no need for a store. When the file lands we kick off a POST,
  // show a percentage, then redirect to the job-detail page.
  let dragover = false;
  let busy = false;
  let progressPct = 0;
  let errorMsg = '';
  let chosenFile: File | null = null;

  // Pipeline options. Defaults match the FastAPI route's defaults.
  let options: JobOptions = {
    preset: 'section',
    scale: '1/4',
    for_print: false,
    with_poche: true,
    default_width: 0.25
  };

  function onPickFile(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      chosenFile = input.files[0];
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    dragover = false;
    const f = e.dataTransfer?.files?.[0];
    if (f) chosenFile = f;
  }

  async function submit() {
    if (!chosenFile) return;
    errorMsg = '';
    busy = true;
    progressPct = 0;
    try {
      const created = await createJob(chosenFile, options, (pct) => {
        progressPct = pct;
      });
      // Sync runner: the response already has status=done. Either way,
      // the job-detail page's poll loop converges fast.
      await goto(`/jobs/${encodeURIComponent(created.job_id)}`);
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
      busy = false;
    }
  }
</script>

<section class="space-y-6">
  <header class="space-y-2">
    <h1 class="text-2xl font-semibold tracking-tight">Upload a Rhino-exported .ai or .pdf</h1>
    <p class="text-ink-500 text-sm">
      We rewrite stroke widths per color tier and (optionally) inject solid-black poché into
      <code class="rounded bg-ink-100 px-1">ClippingPlaneIntersections</code> layers.
      Output preserves every original Illustrator layer.
    </p>
  </header>

  <div
    class="rounded-xl border-2 border-dashed transition-colors p-10 text-center cursor-pointer
           {dragover ? 'border-ink-700 bg-white' : 'border-ink-300 bg-white'}"
    on:dragenter|preventDefault={() => (dragover = true)}
    on:dragover|preventDefault={() => (dragover = true)}
    on:dragleave={() => (dragover = false)}
    on:drop={onDrop}
    role="button"
    tabindex="0"
  >
    <label class="block cursor-pointer space-y-2">
      <input type="file" accept=".ai,.pdf" class="sr-only" on:change={onPickFile} />
      <div class="text-ink-700 text-base">
        {chosenFile ? chosenFile.name : 'Drag a .ai or .pdf here, or click to choose'}
      </div>
      {#if chosenFile}
        <div class="text-xs text-ink-500">
          {(chosenFile.size / 1024 / 1024).toFixed(2)} MB
        </div>
      {/if}
    </label>
  </div>

  <fieldset class="grid grid-cols-2 gap-4 rounded-lg border border-ink-300 bg-white p-4 text-sm">
    <legend class="px-2 text-ink-700 font-medium">Pipeline options</legend>

    <label class="space-y-1">
      <span class="block text-ink-500">Preset</span>
      <select bind:value={options.preset} class="w-full rounded border border-ink-300 px-2 py-1">
        <option value="section">section</option>
        <option value="plan">plan</option>
        <option value="elevation">elevation</option>
        <option value="detail">detail</option>
      </select>
    </label>

    <label class="space-y-1">
      <span class="block text-ink-500">Scale</span>
      <select bind:value={options.scale} class="w-full rounded border border-ink-300 px-2 py-1">
        <option value="1/16">1/16"</option>
        <option value="1/8">1/8"</option>
        <option value="1/4">1/4"</option>
        <option value="1/2">1/2"</option>
      </select>
    </label>

    <label class="space-y-1">
      <span class="block text-ink-500">Default width (pt)</span>
      <input
        type="number"
        step="0.05"
        min="0.05"
        bind:value={options.default_width}
        class="w-full rounded border border-ink-300 px-2 py-1"
      />
    </label>

    <div class="flex flex-col gap-2 pt-5">
      <label class="flex items-center gap-2">
        <input type="checkbox" bind:checked={options.for_print} />
        <span>ISO-128 print weights</span>
      </label>
      <label class="flex items-center gap-2">
        <input type="checkbox" bind:checked={options.with_poche} />
        <span>Inject poché on cut layers</span>
      </label>
    </div>
  </fieldset>

  <div class="flex items-center gap-4">
    <button
      type="button"
      class="rounded-md bg-ink-900 text-ink-100 px-5 py-2 text-sm font-medium
             hover:bg-ink-700 disabled:opacity-50 disabled:cursor-not-allowed"
      on:click={submit}
      disabled={busy || !chosenFile}
    >
      {busy ? 'Uploading…' : 'Apply hierarchy'}
    </button>

    {#if busy}
      <div class="flex-1">
        <div class="h-2 w-full bg-ink-100 rounded">
          <div
            class="h-2 bg-ink-700 rounded transition-all"
            style="width: {progressPct}%"
          ></div>
        </div>
        <div class="mt-1 text-xs text-ink-500">{progressPct}% uploaded — running pipeline…</div>
      </div>
    {/if}
  </div>

  {#if errorMsg}
    <div class="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
      {errorMsg}
    </div>
  {/if}
</section>
