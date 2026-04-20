import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// IMPORTANT: Do NOT expose secret API keys to the browser here.
// Anything read via import.meta.env.VITE_* is bundled and public.
// Server-side secrets (Gemini, Supabase service_role) live only in the
// FastAPI backend's environment on Hugging Face Spaces.
export default defineConfig({
  envDir: '..',           // read the single `.env` at repo root
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
  plugins: [react()],
});
