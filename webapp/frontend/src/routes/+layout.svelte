<script lang="ts">
  // Root layout — applies the global stylesheet and renders a plain header
  // above every page. No authentication state to thread yet, so this is
  // intentionally bare.
  import '../app.css';
</script>

<div class="min-h-screen flex flex-col">
  <header class="border-b border-ink-300 bg-white">
    <div class="mx-auto max-w-3xl flex items-center justify-between px-6 py-4">
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

  <main class="flex-1 mx-auto w-full max-w-3xl px-6 py-10">
    <slot />
  </main>

  <footer class="border-t border-ink-300 text-xs text-ink-500">
    <div class="mx-auto max-w-3xl px-6 py-4">
      Phase D scaffold — local-only, no auth, no payments.
    </div>
  </footer>
</div>
