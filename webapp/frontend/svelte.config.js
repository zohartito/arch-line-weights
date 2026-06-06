import adapter from '@sveltejs/adapter-vercel';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  // SvelteKit's vitePreprocess handles TS in <script lang="ts"> blocks
  // and PostCSS in <style> blocks (so Tailwind directives Just Work).
  preprocess: vitePreprocess(),

  kit: {
    // Vercel adapter enables PR preview deploys (webapp/frontend root). The
    // FastAPI backend stays local; previews are UI-only unless VITE_API_BASE_URL
    // is set to a hosted API later.
    adapter: adapter({
      runtime: 'nodejs22.x'
    })
  }
};

export default config;
