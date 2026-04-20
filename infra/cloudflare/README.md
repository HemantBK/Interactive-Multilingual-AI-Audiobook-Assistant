# Cloudflare Pages (frontend)

## Create the Pages project

1. Sign in at https://cloudflare.com
2. **Workers & Pages → Create → Pages → Connect to Git**
3. Select your GitHub repo (`Interactive-Multilingual-AI-Audiobook-Assistant`)
4. Build settings:
   - Framework preset: **Vite**
   - Build command: `cd frontend && npm ci && npm run build`
   - Build output directory: `frontend/dist`
   - Root directory: `/`
5. Environment variables (Production & Preview):
   - `VITE_API_BASE_URL` = `https://<hf-username>-aria-api.hf.space`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_SENTRY_DSN_FRONTEND` (Week 4)
   - `VITE_POSTHOG_API_KEY` (Week 4)

## Headers

`infra/cloudflare/_headers` is copied into `frontend/public/_headers` by the build step so Cloudflare applies HSTS + CSP automatically. (We'll wire the copy in Week 1 Day 2.)

## Preview URLs

Every PR gets a preview deploy at `<pr-branch>.<project>.pages.dev` — useful for QA before merging to `main`.
