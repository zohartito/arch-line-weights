import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  // SvelteKit's vitePreprocess handles TS in <script lang="ts"> blocks
  // and PostCSS in <style> blocks (so Tailwind directives Just Work).
  preprocess: vitePreprocess(),

  kit: {
    // adapter-auto picks Node by default in dev. For real deploys we'd swap
    // in @sveltejs/adapter-node and run behind the FastAPI service or a
    // reverse proxy.
    adapter: adapter()
  }
};

export default config;
