# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Week 1 Day 1 — Repo restructure
- Apache-2.0 license applied
- Repo reorganized into `frontend/`, `backend/`, `infra/`, `eval/`, `docs/`
- FastAPI backend skeleton with `/health` endpoint
- Initial Supabase schema migration (`infra/supabase/migrations/0001_initial_schema.sql`)
- Hugging Face Space Docker config
- `.env` loaded from repo root by both backend (absolute path in `config.py`) and frontend (`envDir` in `vite.config.ts`)
- Documentation stubs: `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/DEPLOY.md`

### Week 1 Day 1 — Gemini client removal (pulled forward from Week 3)
- **Security**: removed client-side Gemini SDK entirely — no more API key exposure risk from the browser.
- Deleted `frontend/src/services/_legacy_gemini.ts`.
- Added `frontend/src/services/api.ts`: typed HTTP client for the FastAPI backend. Same function signatures as before so `App.tsx` keeps compiling; each AI stub throws `BackendNotReadyError` with the week the real endpoint arrives.
- Removed `@google/genai` from `frontend/package.json` and its `importmap` entry in `frontend/index.html`.
- **UI effect**: upload / translate / narrate / ask will now surface a clear "Backend endpoint coming in Week X" error until each route lands. Navigation and layout still work.
