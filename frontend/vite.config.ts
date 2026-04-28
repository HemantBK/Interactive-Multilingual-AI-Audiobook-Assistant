import { copyFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { type Plugin, defineConfig } from 'vite';

// IMPORTANT: do NOT expose secret API keys to the browser here.
// Anything read via import.meta.env.VITE_* is bundled and public.
// Server-side secrets (Groq, Supabase service_role, paid Gemini) live only
// in the FastAPI backend's environment on Hugging Face Spaces.

const __dirname = dirname(fileURLToPath(import.meta.url));

// Cloudflare Pages reads `_headers` from the build output root. We keep the
// canonical file at infra/cloudflare/_headers and copy it into dist/ at build
// time so there's a single source of truth.
function copyCloudflareHeaders(): Plugin {
  const src = resolve(__dirname, '..', 'infra', 'cloudflare', '_headers');
  const dest = resolve(__dirname, 'dist', '_headers');
  return {
    name: 'aria-copy-cloudflare-headers',
    apply: 'build',
    closeBundle() {
      if (!existsSync(src)) {
        this.warn(`_headers source missing at ${src}; skipping copy`);
        return;
      }
      copyFileSync(src, dest);
    },
  };
}

export default defineConfig({
  envDir: '..',
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
  plugins: [react(), copyCloudflareHeaders()],
});
