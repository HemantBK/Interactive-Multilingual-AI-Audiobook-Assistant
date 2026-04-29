# Quickstart

Get ARIA running locally in 5 minutes.

## Prerequisites

- Python 3.11+
- Node 20+
- Tesseract OCR + Indic language packs:
  ```bash
  # macOS
  brew install tesseract tesseract-lang
  # Debian/Ubuntu
  sudo apt-get install tesseract-ocr tesseract-ocr-{eng,hin,tam,ben,mar,tel}
  # Windows
  choco install tesseract
  ```
- A Supabase project (free tier, region `ap-south-1` recommended)
- A Groq API key (free at https://console.groq.com)

## 1. Clone and configure

```bash
git clone <repo-url> aria && cd aria
cp .env.example .env
```

Edit `.env`:

```bash
# REQUIRED
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_KEY=eyJhbGciOi...   # backend only
GROQ_API_KEY=gsk_...

# Frontend mirrors (VITE_ prefix → bundled into browser, public-safe)
VITE_API_BASE_URL=http://localhost:7860
VITE_SUPABASE_URL=https://<your-project>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOi...

# OPTIONAL (Day 22 observability)
VITE_SENTRY_DSN_FRONTEND=
VITE_POSTHOG_API_KEY=
```

## 2. Apply Supabase migrations

In the Supabase SQL Editor, run in order:

1. `infra/supabase/migrations/0001_initial_schema.sql` — 10 tables + RLS + storage buckets
2. Enable `pg_cron` extension: Database → Extensions → toggle on
3. `infra/supabase/migrations/0002_pg_cron_jobs.sql` — 4 cleanup schedules
4. `infra/supabase/migrations/0003_search_chunks_fn.sql` — vector search RPC
5. `infra/supabase/migrations/0004_user_usage_bump_fn.sql` — atomic quota counter

Verify (`select tablename from pg_tables where schemaname='public';`) → 10 tables.

## 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860
```

Visit http://localhost:7860/health → expect `{"status":"ok",...}`.

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173. Sign in with the magic link or Google.

## 5. Try it

1. Drop a PDF into the upload area (any short doc works).
2. Wait until the doc shows `Ready` (~30 s for the first one — bge-m3 cold-loads ~568 MB).
3. Click the doc. Source viewer renders on the right.
4. Ask a question. Answer streams in with citations.
5. Click a citation → viewer scrolls to that page + highlights the chunk.

## Run the tests

```bash
# Backend (unit + contract; integration auto-skipped)
cd backend
pip install -r requirements-dev.txt
pytest

# Frontend type check
cd frontend
npm run typecheck

# E2E + a11y (Playwright)
npm run test:e2e:install   # one-time browser install
npm run test:e2e
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing VITE_SUPABASE_URL` on `npm run dev` | Make sure `.env` is at the **repo root**, not under `frontend/` |
| Backend imports fail with `ImportError: pdfplumber` | `pip install -r backend/requirements.txt` — you skipped step 3 |
| `tesseract is not installed` on first PDF upload | Install per the prerequisites table above |
| Frontend renders but RAG returns 503 | Check `GROQ_API_KEY` in `.env`; check `KILL_SWITCH=false` |
| `permission denied for relation auth.users` | Apply the migrations against the real Supabase project, not a local Postgres |

## Where next

- Build a feature → [CONTRIBUTING.md](CONTRIBUTING.md)
- Understand the system → [ARCHITECTURE.md](ARCHITECTURE.md)
- Deploy to staging → [DEPLOY.md](DEPLOY.md)
- Self-host the eval suite → [`../eval/README.md`](../eval/README.md)
