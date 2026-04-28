# Hugging Face Space (backend)

## Create the Space

1. Sign in at https://huggingface.co
2. **New Space** → Owner = your username, Space name = `aria-api`, SDK = **Docker**, Visibility = public, Hardware = CPU basic (free)
3. Keep the default Dockerfile prompt; we'll push ours.

## Link to this repo

Option A — push directly:
```bash
# from repo root
git remote add hf https://huggingface.co/spaces/<YOUR_USERNAME>/aria-api
# HF Space expects a Dockerfile at the ROOT of the Space repo, not inside backend/.
# We use a monorepo-friendly approach: add a Dockerfile at Space root that COPYs backend/.
```

Option B (recommended) — GitHub sync via Actions (set up in Week 4 Day 24):
the `.github/workflows/backend-deploy.yml` workflow will `rsync` only `backend/` into the HF Space repo on every push to `main`.

## Space secrets

Go to **Settings → Repository secrets** in the Space and add:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GROQ_API_KEY` — primary LLM, free tier (build plan A2 §3)
- `GEMINI_API_KEY` — paid-only fallback; leave blank in v1
- `CORS_ORIGINS` — your Cloudflare Pages URL (e.g. `https://aria.pages.dev`)
- `SENTRY_DSN_BACKEND` (wired Week 4 Day 22)

## Expected behaviour

Once deployed, `https://<username>-aria-api.hf.space/health` returns:
```json
{"status":"ok","service":"aria-api","version":"0.1.0","env":"production"}
```

## Notes

- HF Spaces on free tier **sleep after ~48h of inactivity**. First request after sleep takes ~30s. Acceptable for v1.
- Port must be **7860** — hard-coded in `backend/Dockerfile`.
