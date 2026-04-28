# ADR 0001 — Stack choice (Build Plan A2)

- **Date**: 2026-04-28
- **Status**: Accepted
- **Deciders**: Hemant
- **Supersedes**: PLAN.md (proposal), `build plan A.md` (interim)

## Context

ARIA is a multilingual AI reader for books and PDFs with precise citations and native-quality Indic TTS. v1 must be free at < 50 DAU, license-clean, and upgradeable as users / money arrive.

Two earlier plans had blocking issues:

- **PLAN.md** chose PyMuPDF (AGPL-3.0 — conflicts with our Apache-2.0 promise) and free Gemini API for everything (free Gemini ToS allows training on inputs — conflicts with the "no training on user data" promise).
- **build plan A.md** fixed those two but missed 16 production-lifecycle items (idempotency, prompt versioning, DR, capacity planning, i18n, a11y, etc.).

`build plan A2.md` resolves both by locking the stack below and addressing all 27 lifecycle items.

## Decision

| Layer | Choice | License |
|---|---|---|
| Frontend framework | React 19 + Vite | MIT |
| Frontend UI | Tailwind + shadcn/ui (Day 7+) | MIT |
| Frontend host | Cloudflare Pages | proprietary, free |
| Backend | Python 3.11 + FastAPI | MIT |
| Backend host (v1) | Hugging Face Spaces (Docker) | proprietary, free |
| Backend host (v1.5 trigger) | Fly.io shared-CPU | proprietary, free |
| DB / Auth / Storage / Vectors | Supabase | open-core, free → $25/mo |
| Vector index | pgvector + HNSW + `halfvec(1024)` | PostgreSQL |
| OCR (primary) | Tesseract 5 (pytesseract) | Apache-2.0 |
| OCR (fallback, paid only) | Gemini 2.5 Flash vision | proprietary |
| PDF parsing | **pdfplumber** (replaces PyMuPDF) | MIT |
| Chunking | `RecursiveCharacterTextSplitter` + Indic separators | MIT |
| Embeddings | `BAAI/bge-m3` (local CPU) | MIT |
| LLM (primary) | **Groq Llama 3.3 70B** | API: proprietary; weights: Llama license |
| LLM (paid fallback) | Gemini 2.5 Flash | proprietary |
| Reranker | `bge-reranker-v2-m3` (local CPU) | MIT |
| TTS (primary) | edge-tts | reverse-engineered, no SLA |
| TTS (fallback) | Piper | MIT |
| Reliability | tenacity (retries) + pybreaker (circuit breakers) | Apache-2.0 |
| i18n | react-i18next | MIT |
| a11y | axe-core in CI | MPL-2.0 |
| Cron | Supabase pg_cron | PostgreSQL |
| DR / backups | Cloudflare R2 (daily Supabase pg_dump) | proprietary, free |
| Observability | Sentry @ 10% sample + PostHog | proprietary, free |
| CI/CD | GitHub Actions | proprietary, free |
| License | Apache 2.0 | — |

**Supply-chain rule**: CI (`.github/workflows/ci.yml`) blocks any direct or transitive AGPL / SSPL / Commons-Clause dependency on every PR.

## Consequences

**Positive**:
- Apache-2.0 promise honored (no AGPL anywhere).
- "No training on user data" honored — user content never reaches free Gemini.
- bge-m3 local embeddings remove the Gemini RPD ceiling at 100 DAU.
- One-flag upgrade path: Groq → Haiku 4.5 ($5/mo) → Sonnet 4.6 ($30–60/mo).
- All 14 listed languages reachable via edge-tts + Piper without per-call cost.

**Negative / risks**:
- HF Spaces free tier sleeps after idle; cold-start 30–90 s. Mitigated by UptimeRobot 5-min `/health` ping (best-effort) and v1.5 trigger to Fly.io (3 always-on free VMs).
- pdfplumber is ~10% slower than PyMuPDF on large PDFs.
- Edge-TTS has no SLA — Piper fallback wired behind the same `tts.synthesize()` interface; one config flip switches.
- Single HF worker = 1 indexing job concurrent; surplus uploads queue with `status='queued'`. Documented limit, not silently dropped.
- Free Supabase 500 MB DB caps at ~50 DAU on this design; capacity watermark in §25 of A2 triggers Pro upgrade automatically.

## Alternatives considered

- **PyMuPDF**: rejected — AGPL-3.0 contaminates derivative work hosted as a service.
- **Free Gemini for embeddings + LLM**: rejected — RPD ceiling breaks at 100 DAU; ToS allows training on inputs.
- **Claude API as primary LLM**: deferred — paid from request 1; better v2 choice when paid tier is sustainable.
- **Self-hosted Qdrant for vectors**: rejected — operational cost > Supabase pgvector at this scale.
- **Coqui XTTS-v2 instead of Piper**: viable; Piper chosen for smaller CPU footprint on the 2-vCPU HF Space.
- **PyMuPDF4LLM (MIT wrapper around PyMuPDF)**: still pulls AGPL PyMuPDF transitively — rejected.

## References

- [build plan A2.md](../../build%20plan%20A2.md) §3 (locked stack), §0 (delta vs A), §15 (CI license guard).
- [build plan A.md](../../build%20plan%20A.md) §0 (audit fixes vs PLAN.md).
- [PLAN.md](../../PLAN.md) (original, retained for history).
