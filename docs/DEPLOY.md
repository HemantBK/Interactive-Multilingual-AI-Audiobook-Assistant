# Deploy

## Environments

| Env | Frontend | Backend | DB |
|---|---|---|---|
| local | Vite dev server `:5173` | uvicorn `:7860` | Supabase cloud (dev project) |
| preview | `<branch>.aria.pages.dev` (Cloudflare auto) | main HF Space (no per-PR Space in v1) | Supabase cloud (dev project) |
| production | `aria.pages.dev` (or custom domain) | `<user>-aria-api.hf.space` | Supabase cloud (prod project) |

## CI gates (runs on every PR + push to main)

Defined in `.github/workflows/ci.yml`. All jobs must pass before merge.

| Job | What it catches |
|---|---|
| `secret-scan` | gitleaks against full git history |
| `license-guard-backend` | AGPL / SSPL / Commons-Clause in Python deps |
| `license-guard-frontend` | AGPL / SSPL / Commons-Clause in npm deps |
| `typecheck-frontend` | TypeScript errors via `tsc --noEmit` |
| `no-client-side-ai` | AI provider SDKs / VITE_*_KEY / direct provider URLs in frontend |
| `backend-lint` | `ruff check backend/` |
| `backend-tests` | `pytest -m 'not integration'` (unit + contract) |
| `migration-safety` | apply every `infra/supabase/migrations/*.sql` against pgvector + auth stub |
| `sbom` | `syft` SPDX-JSON, attached as artifact (non-blocking) |
| `e2e-and-a11y` | Playwright smoke + axe-core scan |

## Nightly (separate workflow)

`eval-nightly.yml` — runs at 03:00 IST against the live golden set.
Posts the report as a workflow artifact. Day 27/28 wires this as a deploy gate.

## First-time deploy (Day 2)

### 1. Supabase
Follow `infra/supabase/README.md`.

### 2. Hugging Face Space (backend)
Follow `infra/hf-space/README.md`. Set Space secrets (`SUPABASE_URL`,
`SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`, `CORS_ORIGINS`,
`SENTRY_DSN_BACKEND`).

### 3. Cloudflare Pages (frontend)
Follow `infra/cloudflare/README.md`. Cloudflare's GitHub integration
auto-creates a preview deployment per PR branch — no extra workflow
needed. Production builds run on every push to `main`.

## Ongoing deploys

### Frontend
- Cloudflare Pages auto-deploys: every push to `main` builds a new prod
  release; every push to a feature branch builds a `<branch>.<project>.pages.dev`
  preview. CI must be green before Cloudflare promotes.

### Backend
- HF Space deploys via `infra/hf-space/deploy.sh`, run from the dev box
  for v1 (manual). Day 28 + the v1.5 trigger move this into a workflow
  job that rsyncs `backend/` after CI passes.

## PR previews

| Surface | Preview behaviour |
|---|---|
| Frontend (Cloudflare Pages) | Auto-deploy per PR branch; URL posted as a check |
| Backend (HF Space) | **No per-PR preview in v1** — too expensive on free tier (each Space is its own container). PRs run `migration-safety` + `backend-tests` on shadow Postgres + ASGI TestClient. Real provider integration tested via `RUN_INTEGRATION=1` from a developer box. |

## Rollback

- **Frontend**: Cloudflare Pages dashboard → Deployments → "Rollback to this deployment"
- **Backend**: revert the commit on `main`; next deploy is the rollback. (HF Spaces has no one-click rollback; Git revert is canonical.)
- **DB**: migrations are forward-only; from `0002` onward every migration ships with a `down.sql` block. The `migration-safety` job applies the up-block on a shadow DB; rollback is `psql -f down.sql` against the same target.

## Deploy gate matrix (Day 27/28 enables)

A green CI status alone doesn't promote to production. The gate is:

```
all CI jobs green                         → required
+ no Tier-1 SLO regression in eval        → enabled Day 27 (compares to last green report)
+ kill_switch off in production           → operator check
```

Until Day 27, eval results are advisory — failures show as warnings on
the PR but don't block merge.
