<script lang="ts">
  // Root layout — applies the global stylesheet and renders a plain header
  // above every page. No authentication state to thread yet, so this is
  // intentionally bare.
  import '../app.css';

  const isVercelUiPreview =
    (import.meta as unknown as { env: Record<string, string> }).env?.VITE_DEPLOY_TARGET ===
    'vercel';
</script>

<div class="min-h-screen flex flex-col">
  <header class="border-b border-ink-300 bg-white">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
      <a href="/" class="font-semibold tracking-tight text-ink-900 hover:text-ink-700">
        arch-line-weights
      </a>
      <a
        href="https://github.com/zohartito/arch-line-weights"
        class="text-sm text-ink-500 hover:text-ink-900"
        rel="noopener noreferrer"
        target="_blank">github</a
      >
    </div>
  </header>

  <main class="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
    <slot />
  </main>

  <footer class="border-t border-ink-300 text-xs text-ink-500">
    <div class="mx-auto max-w-6xl px-6 py-4">
      {#if isVercelUiPreview}
        Vercel UI preview — FastAPI console API not on this host; use local
        <code class="text-ink-700">arch-lw-web-console</code> for full runs. Posting NO-GO.
      {:else}
        Local designer-console prototype — no public proof clearance, no desktop packaging
        claim.
      {/if}
    </div>
  </footer>
</div>
