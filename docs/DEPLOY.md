# Deploy

## Environments

| Env | Frontend | Backend | DB |
|---|---|---|---|
| local | Vite dev server `:5173` | uvicorn `:7860` | Supabase cloud (dev project) |
| preview | `<branch>.aria.pages.dev` | HF Space (branch tag) | Supabase cloud (dev project) |
| production | `aria.pages.dev` (or custom domain) | `<user>-aria-api.hf.space` | Supabase cloud (prod project) |

## First-time deploy (Day 2)

### 1. Supabase
Follow `infra/supabase/README.md`.

### 2. Hugging Face Space (backend)
Follow `infra/hf-space/README.md`.
Set Space secrets, push the `backend/` Docker image.

### 3. Cloudflare Pages (frontend)
Follow `infra/cloudflare/README.md`.
Set env vars, connect to GitHub repo.

## Ongoing deploys

- Merge to `main` → GitHub Actions runs `ci-tests.yml` (unit + integration + eval)
- On green, `frontend-deploy.yml` pushes to Cloudflare Pages
- On green, `backend-deploy.yml` rsyncs `backend/` to the HF Space repo → triggers rebuild

## Rollback

- Frontend: Cloudflare Pages dashboard → Deployments → "Rollback to this deployment"
- Backend: revert the commit on `main`; next deploy is the rollback. (HF Spaces has no one-click rollback; Git revert is canonical.)
- DB: migrations are forward-only; every schema change requires a matching `down` block in the migration file from Week 2 onward
