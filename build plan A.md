# ARIA — Build Plan A (v1, post-audit)

> **Supersedes [PLAN.md](PLAN.md).** Same product, same scope, same 4-week timeline. All 14 issues from the audit are fixed. Differences are summarized in §0.

> **One-liner:** A multilingual AI reader for books and PDFs with **precise citations**, native-quality Indic voices, and a free-at-v1-scale stack.
>
> **Moat:** Citation Mode (every RAG answer maps to the exact paragraph + bounding box in the source) + native Indic TTS/translation. General-purpose product, focused audience.
>
> **License:** Apache 2.0, with a license-clean dependency tree (no AGPL/SSPL anywhere).

---

## 0. What changed from PLAN.md

| # | Change | Reason |
|---|---|---|
| 1 | **PyMuPDF → pdfplumber (MIT)** | PyMuPDF is AGPL-3.0; conflicts with our Apache-2.0 promise |
| 2 | **bge-m3 (local CPU) is the primary embedding** — Gemini removed for embeddings | Gemini free-tier RPD breaks at 100 DAU; bge-m3 is multilingual + Indic-strong |
| 3 | **Groq Llama 3.3 70B = primary LLM**; Gemini Flash is fallback **only on paid key** | Free Gemini ToS allows training on inputs; we cannot promise "no training" while using it |
| 4 | **bge-reranker-v2-m3 added** for retrieval rerank | Keyword overlap is too weak for ≥90% citation precision target |
| 5 | **Piper TTS added as license-clean fallback** to Edge-TTS | Edge-TTS is reverse-engineered, no SLA; need a real fallback |
| 6 | **`bbox jsonb` column added** on `document_chunks` | Char offsets don't map to PDF render coords; bboxes are needed for in-viewer highlight |
| 7 | **Indic-aware chunking** (custom separators incl. `।`, `॥`) | Default splitter cuts Hindi/Tamil mid-sentence |
| 8 | **Cleanup at 14 days, not 30; chunk text offloaded to Storage (not DB)** | Free Supabase 500 MB DB caps at ~50 DAU on the original design |
| 9 | **Golden eval set work starts Week 1, not Week 4** | Day 23 was too late; Kaggle batch labeling answers Open Q #2 |
| 10 | **Dogfooding starts Week 2 Day 14** | Day 28 only is too late to find serious bugs |
| 11 | **Honest latency targets: warm vs cold P95** | HF Spaces sleep + cold start (~30–90s) makes a flat 3s P95 impossible |
| 12 | **Cost model rewritten**: $0 at v1 (0–50 DAU) → ~$25/mo at v1.5 (50–200 DAU) | Free Supabase will not last to 100 DAU — be honest now, not at incident time |
| 13 | **Sentry sampling at 10% from Day 1** | 5K events/mo free quota burns in one bad deploy |
| 14 | **AGPL/SSPL guard added** in CI | Prevent future license-drift slips |

---

## 1. Scope

### v1 IN
- Upload any **PDF / image / text file** (≤ 50 MB)
- Text extraction with **Tesseract** (primary). Gemini Vision is fallback, **paid-only**, gated by env flag.
- Narrate full doc or selection in **14 languages** via **Edge-TTS** (Piper fallback)
- Translate to any of 14 languages — Groq Llama 3.3 70B, cached
- Ask questions with RAG — **every answer highlights the exact source text with page + char range + bounding box**
- Supabase Auth (magic link + Google OAuth); login optional, required to save history
- Per-user + per-IP rate limits, audit logging, error tracking

### v1 OUT
Video / YouTube ingestion, voice input, flashcards, quizzes, voice cloning, mobile app, offline mode, sharing.

### Non-goals (never)
- Hosting pirated or copyrighted books
- Storing uploaded docs > 14 days unless user opts in (changed: 30 → 14)
- Training any model on user data — and we **do not send** user data to providers whose free tier trains on it (rules out free Gemini for any content path)

---

## 2. Architecture

```
┌──────────────────┐       HTTPS + JWT        ┌─────────────────────────┐
│  React + Vite    │ ───────────────────────▶ │   FastAPI (Python 3.11) │
│  Cloudflare Pages│ ◀─────────────────────── │   Hugging Face Spaces   │
└──────────────────┘   SSE streaming (RAG)    └──────────┬──────────────┘
                                                         │
                  ┌──────────────────────────────────────┼──────────────────────────────────────┐
                  ▼                                      ▼                                      ▼
   ┌────────────────────────┐         ┌──────────────────────────────┐         ┌────────────────────────┐
   │ Supabase                │         │ Local CPU models (bundled)   │         │ External APIs          │
   │ • Postgres + pgvector   │         │ • bge-m3 (embed, 1024-d)     │         │ • Groq (LLM, primary)  │
   │ • Auth                  │         │ • bge-reranker-v2-m3         │         │ • Edge-TTS (best Indic)│
   │ • Storage               │         │ • Tesseract (OCR)            │         │ • Piper (TTS fallback) │
   │ • RLS, pg_cron          │         │ • Piper voices (TTS)         │         │ • Gemini (paid only)   │
   └─────────────────────────┘         └──────────────────────────────┘         └────────────────────────┘
                                                                                  server-side keys only
```

**Request flow — upload & index:**
1. Client uploads file → presigned URL → Supabase Storage.
2. Client calls `POST /documents` with storage key.
3. Backend (FastAPI BackgroundTask): extract text (Tesseract for images; **pdfplumber** for PDFs preserving page + word bbox), chunk with **Indic-aware separators** (500 tokens, 50 overlap), embed (**local bge-m3**, 1024-d halfvec), store in `document_chunks` with `(page, char_start, char_end, bbox)`. Chunk text itself is written to Storage, not DB.
4. Background task updates `documents.status` → `ready`. Frontend polls `/documents/:id`.
5. **Concurrency:** 1 active indexing job per worker (HF free = 1 worker). Surplus uploads sit in `documents` with `status='queued'`; a startup hook drains them. Documented limit, not silently dropped.

**Request flow — RAG with citation:**
1. Client `POST /rag/ask { document_id, question }`.
2. Backend embeds question (bge-m3) → pgvector HNSW **top-20** → **rerank with bge-reranker-v2-m3** → top-5 → builds prompt with chunk metadata.
3. **Groq Llama 3.3 70B** returns answer in forced JSON: `{ answer, citations: [{chunk_id, quote}] }`.
4. Backend validates each citation truly exists in retrieved chunks; streams via SSE.
5. Frontend highlights both the **char range in extracted text** and the **bbox overlay on the PDF viewer** with "Jump to page N".

---

## 3. Tech stack (locked, license-clean)

| Layer | Choice | License | Why |
|---|---|---|---|
| Frontend | React 19 + Vite | MIT | Already working |
| UI | Tailwind + shadcn/ui | MIT | Accessible |
| Frontend host | Cloudflare Pages | proprietary, free | No card, generous bandwidth |
| Backend | Python 3.11 + FastAPI | MIT | Best AI/NLP ecosystem |
| Backend host (v1) | Hugging Face Spaces (Docker) | proprietary, free | Sleeps when idle — see §7 |
| Backend host trigger to v1.5 | Fly.io shared-CPU (3 always-on free) | proprietary, free | Eliminates cold start when we outgrow HF |
| DB / Auth / Storage / Vectors | **Supabase** | open-core; free→$25/mo | RLS, pgvector, **pg_cron** |
| Vector index | pgvector + HNSW + `halfvec(1024)` | PostgreSQL | bge-m3 native dim |
| OCR (primary) | Tesseract 5 (pytesseract) | Apache-2.0 | Free, CPU-fast |
| OCR (fallback) | Gemini 2.5 Flash vision | proprietary | **Paid key only**; gated by env flag |
| **PDF parsing** | **pdfplumber** | **MIT** | Replaces PyMuPDF; gives page + word bbox; ~10% slower, license-clean |
| Chunking | LangChain `RecursiveCharacterTextSplitter` + Indic separators | MIT | `\n\n`, `।`, `॥`, `\n`, `. `, `? `, `! ` |
| Embeddings | **`BAAI/bge-m3`** via sentence-transformers, local CPU | MIT | Multilingual, Indic-strong, ~100ms/chunk |
| LLM (primary) | **Groq Llama 3.3 70B** | API: proprietary; weights: Llama license | 14400 RPD free; sub-second TTFT; ToS does not train on inputs |
| LLM (fallback) | Gemini 2.5 Flash | proprietary | Paid-key only; off by default |
| Reranker | **`bge-reranker-v2-m3`**, local CPU | MIT | Cross-encoder, ~150ms; lifts citation precision into target range |
| TTS (primary) | `edge-tts` Python lib | reverse-engineered, no SLA | Best Indic; documented as best-effort |
| TTS (fallback) | **Piper** | MIT | Local CPU TTS, license-clean, multi-voice |
| Cache | Supabase tables (`audio_cache`, `translation_cache`) | — | Single source of truth |
| Observability | **Sentry @ 10% sample** + PostHog | proprietary, free | See §9 |
| **Cron** | **Supabase pg_cron** | PostgreSQL | Runs even when HF Space sleeps |
| CI/CD | GitHub Actions | proprietary, free | 2000 min/mo |
| Testing | pytest + pytest-asyncio + Playwright | MIT/BSD | Standard |
| RAG eval | `ragas` + custom golden set | Apache-2.0 | Open |
| License | Apache 2.0 | — | Patent grant; clean tree |

**Supply-chain rule:** CI fails on any direct or transitive AGPL/SSPL/Commons-Clause dep. See §6.

---

## 4. Data model (Postgres / Supabase)

```sql
-- documents
create table documents (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade,
  title text not null,
  source_type text check (source_type in ('pdf','image','text')) not null,
  storage_path text not null,
  page_count int,
  source_language text,
  status text check (status in ('queued','uploading','processing','ready','failed')) not null,
  error_message text,
  created_at timestamptz default now(),
  processed_at timestamptz
);

-- chunks (citation anchors + bounding boxes; text offloaded to Storage)
create extension if not exists vector;
create table document_chunks (
  id bigserial primary key,
  document_id uuid references documents(id) on delete cascade,
  chunk_index int not null,
  text_storage_path text not null,   -- chunk text in Storage, not DB (size mgmt)
  page_number int not null,
  char_start int not null,
  char_end int not null,
  bbox jsonb,                        -- [{page,x0,y0,x1,y1}] word-level boxes for in-PDF highlight
  token_count int,
  embedding halfvec(1024),           -- bge-m3 native dim
  created_at timestamptz default now()
);
create index on document_chunks using hnsw (embedding halfvec_cosine_ops);
create index on document_chunks(document_id);

-- content-addressable caches
create table audio_cache (
  content_hash text primary key,    -- sha256(text|voice|lang)
  voice text not null,
  language text not null,
  storage_path text not null,
  duration_sec numeric,
  size_bytes bigint,
  hit_count int default 0,
  created_at timestamptz default now(),
  last_accessed_at timestamptz default now()
);

create table translation_cache (
  content_hash text primary key,    -- sha256(text|target_lang)
  source_language text,
  target_language text not null,
  translated_text text not null,
  hit_count int default 0,
  created_at timestamptz default now()
);

-- Q&A + feedback
create table conversations (
  id uuid primary key default uuid_generate_v4(),
  document_id uuid references documents(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  question text not null,
  answer text not null,
  cited_chunks bigint[] not null,
  latency_ms int,
  tokens_in int,
  tokens_out int,
  model text,
  user_rating smallint check (user_rating in (-1,0,1)) default 0,
  created_at timestamptz default now()
);

-- usage tracking
create table user_usage_daily (
  user_id uuid not null,
  date date not null,
  documents_uploaded int default 0,
  pages_processed int default 0,
  tts_chars int default 0,
  rag_queries int default 0,
  primary key (user_id, date)
);
```

**Row-Level Security:** every table has RLS enabled.

**Cleanup (Supabase pg_cron, daily 03:00 IST = 21:30 UTC):**
```sql
select cron.schedule('aria_doc_cleanup_14d', '30 21 * * *', $$
  delete from documents
  where created_at < now() - interval '14 days'
    and not exists (select 1 from documents_keepalive k where k.document_id = documents.id);
$$);
```

---

## 5. Repository layout

(Unchanged from PLAN.md §5. The plan already separates `frontend/`, `backend/`, `infra/`, `eval/`, `docs/`. Migration of legacy files happens Week 1 Day 1; deletion of `_legacy_gemini.ts` happens Week 3 Day 20.)

---

## 6. Security threat model

(All threats from PLAN.md §6 carry over. New rows added below.)

| Threat | Control |
|---|---|
| **Supply-chain license drift (AGPL/SSPL slipping in)** | CI step in `ci-tests.yml`: `pip-licenses --fail-on='AGPL*;SSPL*;Commons-Clause'` and `license-checker --excludePackages 'aria-frontend' --failOn 'AGPL-3.0;SSPL-1.0'`. Block merge. Dependabot watches license changes. |
| **Free-LLM training on user inputs** | Gemini paths gated by `GEMINI_PAID_KEY` env flag; absent in v1 production. Only Groq + local models touch user content. Documented in `docs/SECURITY.md`. |
| **TTS endpoint kill (Microsoft revokes Edge-TTS)** | Piper fallback wired behind same `tts.synthesize()` interface; switch is one config flip. Indic Piper voices preloaded in Docker image. |

---

## 7. Cost model — honest free-tier headroom

### v1 (0–50 DAU): **$0/month**

| Resource | Free tier | Headroom at 50 DAU × 14-day retention |
|---|---|---|
| Groq Llama 3.3 70B | 14400 RPD | ~750 RAG calls/day = **5%**, plenty of room |
| bge-m3 embeddings | local CPU, free | Bottlenecked by HF Spaces 1-worker concurrency, not API |
| Edge-TTS / Piper | unmetered | fine |
| Supabase DB | 500 MB | ~75% used (embeddings + metadata only; chunk text in Storage) |
| Supabase Storage | 1 GB | ~50% used (chunk text + audio cache) |
| HF Spaces | sleeps when idle | cold start 30–90s after ~48h idle — see latency targets |
| Cloudflare Pages | unlimited bandwidth | fine |
| Sentry | 5K events/mo @ 10% sample | ~50K real events/mo headroom |
| GitHub Actions | 2000 min/mo | nightly eval ~5min × 30 = 150 min, fine |

### v1.5 (50–200 DAU): **~$25/month**

| Add | Cost | Why |
|---|---|---|
| Supabase Pro | $25/mo | 8 GB DB, daily PITR backups, scales storage with users |
| Move backend HF → Fly.io shared-CPU | $0 (3 free always-on VMs) | Eliminates HF cold start; Docker image is portable |

### v2 (200+ DAU): variable

| Add | Cost ballpark | Why |
|---|---|---|
| Paid Gemini API | usage-based | Re-enable Vision OCR + Flash fallback |
| Upstash Redis | $0–10/mo | Faster cache than Postgres |
| Sentry Team | $26/mo | More events, better dashboards |

### Latency targets, honest

| Path | P95 warm | P95 cold | Cold-rate target |
|---|---|---|---|
| RAG first token | ≤ 3s | ≤ 45s | < 5% of sessions |
| TTS gen / 1k chars | ≤ 5s | ≤ 50s | < 5% |
| Indexing 20-page PDF | ≤ 45s | n/a (always background) | — |

Cold-start mitigation: UptimeRobot 5-min `/health` ping (best-effort, documented as such). Real fix is the v1.5 move to Fly.io.

---

## 8. Evaluation

| Metric | Target | How |
|---|---|---|
| OCR character accuracy | ≥ 95% clean PDFs, ≥ 85% scans | 20-doc golden set (English + Hindi + Tamil) |
| Retrieval hit@5 | ≥ 85% | 50 hand-labeled Q→chunk pairs per priority language |
| Citation precision | ≥ 90% (cited chunk truly contains answer) | LLM-as-judge with Groq Llama on 100 Q/A pairs |
| Answer faithfulness | ≥ 80% | `ragas` faithfulness score |
| Translation BLEU (En→Hi) | ≥ 35 | FLORES-200 subset |
| TTS MOS (naturalness) | ≥ 3.8/5 | Human rating, 20 samples × 5 languages |
| P95 RAG latency (warm) | ≤ 3s | Sentry + PostHog |
| P95 TTS gen | ≤ 5s per 1000 chars | Sentry |

**Golden eval set work begins Week 1**, in parallel with build:
- Kaggle is used for batch OCR ground-truth labeling and to compare bge-m3 vs alternatives on Indic.
- Eval harness wired Week 4 Day 23 and runs nightly in GitHub Actions. Regression > 2% blocks merge.

---

## 9. Observability + ops

- **Sentry**: `traces_sample_rate=0.1`, `profiles_sample_rate=0.0`, errors at full rate. Stays under 5K events/mo at v1 scale.
- **PostHog**: product analytics, funnels (upload → process → first question), feature flags.
- **Structured JSON logs** from FastAPI → HF Space logs.
- **Uptime**: UptimeRobot `/health` 5-min ping (best-effort keep-alive on HF free; not a guarantee).
- **Cron**: Supabase pg_cron — runs server-side regardless of HF Space sleep state.
- **Runbook** (`docs/RUNBOOK.md`): HF cold-start, Groq rate-limit, re-index a stuck doc, free→paid migration playbook, Edge-TTS → Piper switchover.

---

## 10. Build plan (4 weeks)

### Week 1 — Foundation + license-clean stack
| Day | Deliverable |
|---|---|
| 1 | Restructure repo. Apache-2.0 LICENSE. `.env.example`. **Pin pdfplumber, sentence-transformers, bge-m3, bge-reranker, groq, edge-tts, piper-tts in `requirements.txt`. Remove pymupdf and any google-generativeai-for-embeddings.** Add AGPL-guard step to CI. |
| 2 | Supabase project + migrations + RLS + Storage bucket + **pg_cron extension enabled**. HF Space skeleton with FastAPI `/health`. Cloudflare Pages connected to `frontend/`. |
| 3 | Auth: Supabase magic-link + Google OAuth. Frontend `useAuth`. Backend JWT middleware. |
| 4 | Upload endpoint: presigned URL → `POST /documents` → row created as `queued`. 50 MB + MIME + magic-byte validation. EXIF strip on images. |
| 5 | PDF text extraction (**pdfplumber**) with page + word **bbox**. Image OCR (Tesseract). Status transitions: `queued → processing`. |
| 6 | Indic-aware chunking (`। ॥` separators). **Local bge-m3 embedding pipeline** loaded once at startup. pgvector HNSW insertion. **Chunk text written to Storage, not DB.** |
| 7 | E2E smoke test: upload → see chunks in DB with citation metadata + bbox. **Begin building golden eval set on Kaggle (20 docs × 5 languages, ground-truth Q/A).** |

### Week 2 — RAG + Citation Mode + dogfood start
| Day | Deliverable |
|---|---|
| 8 | `POST /rag/ask` with SSE. Top-20 retrieval + **bge-reranker-v2-m3 to top-5**. |
| 9 | Structured output from **Groq Llama 3.3 70B**: `{answer, citations:[{chunk_id, quote}]}`. Backend validates each citation actually exists in the retrieved set. |
| 10 | Frontend chat UI talks to backend (in this commit, delete client-side Gemini calls — see Week 3 Day 20 for legacy file removal). SSE token streaming. |
| 11 | **Dual citation highlighting**: click citation → scroll to page → highlight char range in extracted text **and** bbox overlay on the PDF viewer. |
| 12 | Translation pipeline (Groq) with `translation_cache`. Frontend translate button rewired. |
| 13 | Prompt-injection guard. DOMPurify on all model output. CSP + HSTS headers. |
| 14 | Integration tests for RAG + citations. **Start dogfooding personally** with 3 real PDFs (English, Hindi, Tamil). Open `docs/dogfood-log.md` and update it daily through Week 4. |

### Week 3 — TTS, polish, kill legacy
| Day | Deliverable |
|---|---|
| 15 | **`tts.synthesize()` interface** with edge-tts primary + Piper fallback behind a single env flag. `audio_cache` populated. Chunked synthesis with silence concat. |
| 16 | `POST /tts` streams WAV. Frontend player wired. |
| 17 | Audio player UX: per-paragraph highlight synced to audio (word-level deferred to v1.5). |
| 18 | Rate limiting (slowapi) per-IP + per-user. Daily caps via `user_usage_daily`. Global kill-switch env var. |
| 19 | Error boundaries. Friendly errors. Toasts. |
| 20 | **Delete `_legacy_gemini.ts` and any client-side keys.** Verify with `grep VITE_.*KEY` in `frontend/` returning nothing sensitive. |
| 21 | Manual QA: 10 docs × 5 languages. Burn down dogfood log. |

### Week 4 — Production readiness + launch
| Day | Deliverable |
|---|---|
| 22 | Sentry SDK (10% sample) frontend + backend. PostHog events (upload, question, translate, narrate). |
| 23 | Eval harness: hit@5, citation precision (LLM-as-judge), `ragas` faithfulness. Nightly GitHub Action. Regression > 2% blocks merge. |
| 24 | CI: pytest, Playwright smoke, **license check (`pip-licenses` AGPL-fail + `license-checker` for npm)**, auto-deploy on green merge to `main`. |
| 25 | Supabase pg_cron 14-day cleanup live. User export + delete endpoints. Privacy page. |
| 26 | Security review pass: secret scan, `npm audit`, `pip-audit`, CSP review, auth edge cases, RLS verified with non-owner account. |
| 27 | `docs/` complete: ARCHITECTURE, API (OpenAPI), SECURITY, DEPLOY, RUNBOOK (incl. HF cold-start + free→paid migration + Edge-TTS→Piper switchover). Rewrite root README. |
| 28 | **Launch:** invite 10 testers (classmates, r/IndiaTech, r/developersIndia). Watch Sentry + PostHog live. |

---

## 11. Launch checklist (Day 28)

- [ ] All third-party API keys server-side only (`grep VITE_.*KEY` in `frontend/` returns nothing sensitive)
- [ ] **No AGPL/SSPL deps** anywhere (`pip-licenses` + `license-checker` clean)
- [ ] CSP + HSTS headers live
- [ ] 50 MB upload cap enforced server-side
- [ ] Rate limits active and tested under load
- [ ] Supabase RLS verified with a non-owner account
- [ ] Sentry + PostHog receiving events; Sentry sample = 0.1
- [ ] Eval metrics meet targets on golden set
- [ ] README accurately describes the app + free vs paid path
- [ ] Privacy + Terms + DMCA contact published
- [ ] `/health` monitored by UptimeRobot
- [ ] First 3 PDFs work E2E in Hindi, Tamil, English
- [ ] 14-day pg_cron cleanup runs successfully on a test row
- [ ] Free-tier dashboard: Groq < 50%, Supabase DB < 75%, Storage < 75%, Sentry < 50%
- [ ] **No content sent to free Gemini** (Gemini env flag off; Gemini paths only triggered when paid key present)
- [ ] Edge-TTS → Piper fallback verified manually for at least 3 Indic voices

---

## 12. Open decisions (need your input)

These are independent of the audit fixes:

1. **Domain name** — `ariareads.in`, `readaria.app`, or Cloudflare subdomain for now?
2. **English-first UI with Hindi toggle, or Hindi-first UI?** (DPDP / Indic audience pull is real.)
3. **Telemetry consent** — opt-in or opt-out by default? (DPDP leans opt-in.)

Reply with answers to 1–3 and I start Week 1 Day 1.
