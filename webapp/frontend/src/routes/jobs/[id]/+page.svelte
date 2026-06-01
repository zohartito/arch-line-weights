<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { page } from '$app/stores';
  import { downloadUrl, getJob, type JobDetail } from '$lib/api';

  let detail: JobDetail | null = null;
  let pollHandle: ReturnType<typeof setTimeout> | null = null;
  let errorMsg = '';

  // Backoff schedule: 500 ms, 750 ms, 1.1 s, 1.7 s, 2.5 s, 2.5 s … capped.
  // The sync runner usually finishes in <2 s on synthetic fixtures and
  // 10–60 s on real Rhino exports, so the cap matters for the long tail.
  const POLL_DELAYS_MS = [500, 750, 1100, 1700, 2500];
  let pollIndex = 0;

  function nextDelay(): number {
    const d = POLL_DELAYS_MS[Math.min(pollIndex, POLL_DELAYS_MS.length - 1)];
    pollIndex += 1;
    return d;
  }

  async function tick() {
    try {
      const jobId = $page.params.id;
      if (!jobId) throw new Error('missing job id');
      detail = await getJob(jobId);
      if (detail.status === 'done' || detail.status === 'failed') {
        return; // stop polling — terminal state reached
      }
      pollHandle = setTimeout(tick, nextDelay());
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
    }
  }

  onMount(() => {
    tick();
  });

  onDestroy(() => {
    if (pollHandle) clearTimeout(pollHandle);
  });
</script>

<section class="space-y-6">
  <a href="/" class="text-sm text-ink-500 hover:text-ink-900">&larr; new upload</a>

  {#if errorMsg}
    <div class="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
      {errorMsg}
    </div>
  {/if}

  {#if !detail}
    <p class="text-ink-500">Loading job…</p>
  {:else}
    <header class="space-y-2">
      <h1 class="text-2xl font-semibold tracking-tight">{detail.original_filename}</h1>
      <p class="text-sm text-ink-500">
        Status:
        <span
          class="font-medium {detail.status === 'done'
            ? 'text-emerald-700'
            : detail.status === 'failed'
              ? 'text-red-700'
              : 'text-ink-700'}"
        >
          {detail.status}
        </span>
        · Job ID <code class="rounded bg-ink-100 px-1 text-xs">{detail.job_id}</code>
      </p>
    </header>

    {#if detail.status === 'failed' && detail.error}
      <div class="rounded border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
        {detail.error}
      </div>
    {/if}

    {#if detail.status === 'done' && detail.download_url}
      <a
        href={downloadUrl(detail) ?? '#'}
        class="inline-block rounded-md bg-ink-900 text-ink-100 px-5 py-2 text-sm font-medium hover:bg-ink-700"
      >
        Download processed file
      </a>
    {/if}

    {#if detail.apply_summary}
      <section class="space-y-2">
        <h2 class="text-lg font-semibold">Stroke-width rewrite</h2>
        <dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm bg-white border border-ink-300 rounded p-4">
          <dt class="text-ink-500">Strokes rewritten</dt>
          <dd class="text-ink-900 font-medium">
            {detail.apply_summary.widths_rewritten.toLocaleString()}
          </dd>
          <dt class="text-ink-500">Color changes seen</dt>
          <dd class="text-ink-900 font-medium">
            {detail.apply_summary.xa_seen.toLocaleString()}
          </dd>
          <dt class="text-ink-500">Input → output bytes</dt>
          <dd class="text-ink-900 font-medium">
            {detail.apply_summary.input_size.toLocaleString()} →
            {detail.apply_summary.output_size.toLocaleString()}
          </dd>
          <dt class="text-ink-500">Payload chunks</dt>
          <dd class="text-ink-900 font-medium">
            {detail.apply_summary.chunks_in} → {detail.apply_summary.chunks_out}
          </dd>
        </dl>
      </section>
    {/if}

    {#if detail.poche_summary && detail.fills.length > 0}
      <section class="space-y-2">
        <h2 class="text-lg font-semibold">Poché injection</h2>
        <p class="text-sm text-ink-500">
          Injected {detail.poche_summary.polygons_injected} polygons across
          {detail.poche_summary.layers_injected}/{detail.poche_summary.layers_targeted}
          cut layers.
        </p>
        <div class="overflow-x-auto rounded border border-ink-300 bg-white">
          <table class="min-w-full text-sm">
            <thead class="bg-ink-100 text-ink-700 text-left">
              <tr>
                <th class="px-3 py-2 font-medium">Layer</th>
                <th class="px-3 py-2 font-medium">Strategy</th>
                <th class="px-3 py-2 font-medium text-right">Polys</th>
                <th class="px-3 py-2 font-medium text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {#each detail.fills as fill (fill.layer)}
                <tr class="border-t border-ink-300">
                  <td class="px-3 py-2 font-mono text-xs">{fill.layer.split('::').slice(-1)[0]}</td>
                  <td class="px-3 py-2 text-ink-500">{fill.strategy}</td>
                  <td class="px-3 py-2 text-right">{fill.polygon_count}</td>
                  <td
                    class="px-3 py-2 text-right font-medium {fill.confidence >= 0.85
                      ? 'text-emerald-700'
                      : fill.confidence > 0
                        ? 'text-amber-700'
                        : 'text-red-700'}"
                  >
                    {fill.confidence.toFixed(2)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}
  {/if}
</section>
