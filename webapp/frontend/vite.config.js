import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Vite dev server runs on :5173. The backend lives on :8000 (configurable
// via VITE_API_BASE_URL). We keep them as separate origins rather than
// proxying so production and dev follow the same flow — the SvelteKit app
// can be deployed independently of FastAPI later.
export default defineConfig({
  plugins: [sveltekit()],
  server: {
    port: 5173
  }
});
