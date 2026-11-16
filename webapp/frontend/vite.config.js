import adapter from '@sveltejs/adapter-vercel';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

// Vite dev server runs on :5173. The backend lives on :8000 (configurable
// via VITE_API_BASE_URL). We keep them as separate origins rather than
// proxying so production and dev follow the same flow — the SvelteKit app
// can be deployed independently of FastAPI later.
export default defineConfig({
  plugins: [
    // SvelteKit 3 takes its configuration here; svelte.config.js is no longer read.
    sveltekit({
      // vitePreprocess handles TS in <script lang="ts"> blocks
      // and PostCSS in <style> blocks (so Tailwind directives Just Work).
      preprocess: vitePreprocess(),
      // Vercel adapter enables PR preview deploys (webapp/frontend root). The
      // FastAPI backend stays local; previews are UI-only unless VITE_API_BASE_URL
      // is set to a hosted API later.
      adapter: adapter({
        runtime: 'nodejs22.x'
      })
    })
  ],
  server: {
    port: 5173
  }
});
