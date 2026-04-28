# ARIA — Build Plan A2 (v1, all-tracks)

> **Supersedes [build plan A.md](build%20plan%20A.md).** Same product, same stack, same moat. Extends to cover all 21 production-AI lifecycle items from your audit + 6 cross-cutting tracks (i18n, a11y, DR, capacity, legal, onboarding) we caught.
>
> **Timeline: 6 weeks, not 4.** Solo + new-to-AI + 27 tracks → realistic with you delegating code work to Claude. If you must do 4 weeks, see §29 ("What we cut").
>
> **License:** Apache 2.0, no AGPL/SSPL anywhere.

---

## §0 — What's new vs Plan A

### Patches to existing sections (gaps closed)
| Track | What got added |
|---|---|
| 2 — Ingestion | Eval-set ingestion plan + ingest telemetry |
| 4 — Preprocessing | Dedup, boilerplate strip, Unicode NFC, lang-detect, PII redact |
| 5 — Feature versioning | `embedding_model_version` column on `document_chunks` |
| 6 — Model selection | Benchmark log + experiment tracking + A/B swap capability |
| 9 — Packaging & versioning | Prompt registry, model artifact pinning, API semver, image tags |
| 11 — Pipeline integration | Idempotency keys, retry budgets, circuit breakers per endpoint |
| 12 — Frontend | Component inventory, state machines, empty/loading/error states |
| 14 — Testing | Contract tests, chaos, load, prompt-injection regression, a11y in CI |
| 15 — CI/CD | PR preview envs, secret scan, SBOM, migration safety |
| 16 — Release | Canary via opt-in channel, feature flags, DB migration rollback |
| 17 — Monitoring | SLO definitions + alert thresholds |
| 18 — Audit | audit_log schema + retention + sampling |
| 19 — Feedback | Hard-negative mining + weekly prompt iteration loop |
| 20 — Docs | ADRs + CONTRIBUTING + QUICKSTART + glossary |
| 21 — Cost | Per-user cost attribution + budget-burn alerts |

### New cross-cutting tracks
| § | Track | One-liner |
|---|---|---|
| 22 | i18n | react-i18next; 6 priority locales |
| 23 | a11y | WCAG 2.1 AA; axe-core in CI; NVDA tested |
| 24 | DR / Backups | Daily Supabase → Cloudflare R2; RTO 4h / RPO 24h |
| 25 | Capacity Planning | Watermarks → automated migration-trigger issues |
| 26 | Legal | ToS / Privacy / DMCA / DPDP / GDPR-readiness |
| 27 | Onboarding UX | Sample PDFs, coach marks, welcome email, activation event |

### Explicitly N/A (won't appear)
- **Feature Store** (Feast/Hopsworks) — overkill at this scale
- **Model Training** — pretrained only

---

## §1 — Scope

(Unchanged from Plan A §1. v1 IN: upload + extract + narrate + translate + RAG-with-citation + auth. v1 OUT: video, voice input, flashcards, sharing, mobile app, offline. Non-goals: no pirated content, ≤14-day retention, no training on user data.)

---

## §2 — Architecture

(Unchanged from Plan A §2; one addition — pipeline DAG with explicit retry/idempotency anchors.)

```
upload → [idempotency key check] → Supabase Storage → enqueue job
                                                        │
                                                        ▼
            ┌─ retry: 3, exp backoff 1s/2s/4s, 5min deadline ─┐
            │  extract → preprocess → chunk → embed → index   │
            └────────────────────┬────────────────────────────┘
                                 │
                       ┌─────────┴─────────┐
                       ▼                   ▼
                   status=ready       status=failed → DLQ row → user notified
```

---

## §3 — Tech stack additions on top of Plan A

| Layer | Add | License | Why |
|---|---|---|---|
| i18n | `react-i18next` | MIT | Standard React i18n |
| a11y | `axe-core` (in CI via Playwright) | MPL-2.0 | Catch a11y regressions |
| Decision log | `adr-tools` | MIT | One ADR per major decision |
| Backup | **Cloudflare R2** (free 10 GB) | proprietary, free | Daily Supabase export, separate vendor |
| Load test | **k6 (open-source binary)** | AGPL-3.0 — **only run as a tool, not bundled** | Free; license-safe because it's a CLI we invoke, not a library we link |
| Secret scan | `gitleaks` (CI) | MIT | Stop key leaks pre-merge |
| SBOM | `syft` | Apache-2.0 | Supply-chain transparency |

**k6 license note**: AGPL only contaminates when you *link/distribute* it as a library. We use it as a CLI in CI to test, never bundle. Same way the linux kernel is GPL but using `cat` doesn't make your output GPL.

---

## §4 — Data model — additions on top of Plan A §4

```sql
-- Add to document_chunks
alter table document_chunks
  add column embedding_model_version text not null default 'bge-m3@1.0',
  add column lang_detect text;

-- Prompt registry (so prompts can be A/B'd and rolled back)
create table prompts (
  id text not null,                 -- e.g., 'rag.system'
  version int not null,
  content text not null,
  description text,
  is_active boolean default false,
  created_at timestamptz default now(),
  primary key (id, version)
);
create unique index on prompts (id) where is_active = true;

-- Audit log
create table audit_log (
  id bigserial primary key,
  user_id uuid,
  action text not null,             -- e.g., 'document.upload', 'rag.ask'
  resource_type text,
  resource_id text,
  metadata jsonb,                   -- redacted; never raw user content
  ip_hash text,                     -- sha256(ip || daily_salt)
  created_at timestamptz default now()
);
create index on audit_log (user_id, created_at desc);
create index on audit_log (action, created_at desc);

-- Idempotency
create table idempotency_keys (
  key text primary key,             -- client-provided UUID
  user_id uuid not null,
  endpoint text not null,
  request_hash text not null,
  response jsonb,
  status_code int,
  created_at timestamptz default now()
);
-- Auto-expire after 24h via pg_cron

-- Cost attribution (extend user_usage_daily)
alter table user_usage_daily
  add column cost_usd_estimate numeric(10,4) default 0;
```

---

## §5 — Repository layout

(Unchanged from Plan A §5; adds `docs/adr/`, `frontend/src/locales/`, `eval/feedback/`.)

---

## §6 — Security threat model

(Plan A §6 + threats below.)

| Threat | Control |
|---|---|
| Replay attacks on POST /documents | Idempotency-Key required, 24h TTL |
| Prompt-version drift breaking prod | Active prompt enforced via DB constraint; rollback via version flip |
| Backup theft from R2 | R2 bucket has IP allowlist + service-token; backups encrypted at rest by default |

---

## §7 — Cost model + per-user attribution

(Plan A §7 tier table unchanged.)

**Per-user attribution**: nightly cron updates `user_usage_daily.cost_usd_estimate` =
`(rag_queries × $0) + (tts_chars × $0) + (storage_mb × $0)` while on free tier; formula swaps in Pro pricing on v1.5 trigger.

**Budget-burn alerts** (see §17):
- Supabase any-resource > 70% for 24h
- Groq RPD > 60% for 7d
- Sentry events > 60% mo
- Cloudflare R2 > 50% (DR backups)

---

## §8 — Evaluation

(Plan A §8 + additions.)

**Experiment tracking**: simple JSON log at `eval/experiments/<date>_<slug>.json`. Schema:
```json
{ "date":"...", "component":"reranker", "variant":"bge-reranker-v2-m3 vs cross-encoder/ms-marco-MiniLM",
  "metrics":{...}, "winner":"bge-reranker-v2-m3", "delta":"+4.2% hit@5", "decision":"adopt", "adr":"docs/adr/0007-reranker.md" }
```

**Hard-negative mining**: weekly batch from `conversations.user_rating = -1` and `cited_chunks` where citation was wrong → added to retrieval eval set.

---

## §9 — Model Packaging & Versioning (NEW)

| Artifact | Versioning | Pin location |
|---|---|---|
| bge-m3 weights | HF model commit hash + sha256 | `backend/app/services/embedding.py` constant |
| bge-reranker-v2-m3 | same | same |
| Tesseract data | apt package version pin | Dockerfile |
| System prompts | row in `prompts` table; rolled out by `(id, version)` reference in code | DB |
| API | semver in OpenAPI spec; `Accept-Version: 1` header support | `backend/app/main.py` |
| Docker image | `vMAJOR.MINOR.PATCH` + git SHA | HF Space + GHCR mirror |
| Frontend bundle | git SHA in `<meta name="version">` | `frontend/index.html` |

**Prompt iteration workflow**: change → write new row (`is_active=false`) → run `eval/runners/prompt_compare.py` on 50 golden Q/A → if win > 2%, flip `is_active` → write ADR → log experiment.

---

## §10 — API & Serving

(Unchanged from Plan A. Note: every endpoint exposes `Accept-Version` header for forward-compat.)

---

## §11 — Backend & Pipeline Integration (NEW DETAIL)

| Endpoint | Idempotency key | Retry budget | Deadline | Circuit breaker |
|---|---|---|---|---|
| `POST /documents` | client-provided UUID, required | n/a (client retries) | 30s | n/a |
| Indexing job (internal) | `doc_id` | 3 retries, exp backoff 1s/2s/4s | 5min | open after 5 consecutive 5xx, half-open at 60s |
| `POST /rag/ask` | (read; idempotent by Q+doc_id) | Groq: 2 retries 0.5s/1s | 30s | yes |
| `POST /tts` | `content_hash` | edge-tts: 1 retry → Piper fallback | 60s | yes |
| `POST /translate` | `content_hash` | Groq: 2 retries → cache miss | 15s | yes |

**Library**: `tenacity` for Python retries; `pybreaker` for circuit breakers; both Apache-2.0.

---

## §12 — Frontend & UI (NEW DETAIL)

**Component inventory** (`frontend/src/components/`):
- `Layout/`: AppShell, TopBar, Sidebar, Footer
- `Auth/`: LoginCard, AuthGuard
- `Upload/`: Dropzone, ProgressBar, FileTypeHint
- `Document/`: PdfViewer (with bbox overlay), TextViewer, PageNav
- `Citation/`: CitationCard, CitationHighlight, JumpToPageButton
- `Chat/`: MessageList, MessageInput, StreamingMessage, EmptyChat
- `Audio/`: PlayerBar, VoicePicker, ParagraphHighlight, SpeedControl
- `Translate/`: LangPicker, InlineTranslation
- `Common/`: ErrorBoundary, Toast, LoadingSkeleton, EmptyState, OnboardingCoachmark

**State machines** in `docs/state-machines.md`:
- Upload: `idle → uploading → processing → ready | failed`
- RAG: `idle → asking → streaming → done | error`
- TTS: `idle → synthesizing → playing | error`

**Empty / loading / error trio** for every fetch — checklist in `docs/ui-states.md`.

**Mobile responsive**: tested at 360 / 768 / 1024 / 1440px. No native mobile app v1.

---

## §13 — Auth, Authz & Security

(Unchanged from Plan A §6. Adds: every API request writes a row to `audit_log`.)

---

## §14 — Testing (NEW DETAIL)

| Layer | Tool | Targets | Run on |
|---|---|---|---|
| Unit | pytest, vitest | services/, hooks/, utils/ | every PR |
| Integration | pytest | API ↔ Supabase ↔ external (mocked) | every PR |
| Contract | schemathesis | OpenAPI ↔ implementation | every PR |
| E2E smoke | Playwright | upload → ask → cite → narrate (1 happy path) | every merge to main |
| a11y | axe-core via Playwright | top-5 pages | every PR |
| Prompt-injection regression | pytest + curated payload set | "ignore previous instructions", exfil patterns | every PR |
| Chaos | custom (Python) | Groq 429, Supabase 503, HF cold-start | nightly |
| Load | k6 (CLI) | 50 concurrent uploads, 200 RAG queries/min | weekly + pre-launch |

**Pyramid target**: ~70% unit / 20% integration / 10% E2E.

---

## §15 — CI/CD & MLOps (NEW DETAIL)

| Step | Tool | Blocking? |
|---|---|---|
| Lint | ruff (py), eslint (ts), prettier | ✅ |
| Type check | mypy, tsc --noEmit | ✅ |
| Secret scan | gitleaks | ✅ |
| License check | pip-licenses, license-checker (no AGPL/SSPL bundled) | ✅ |
| SBOM | syft | non-blocking; attached to release |
| Unit + integration | pytest, vitest | ✅ |
| Contract | schemathesis | ✅ |
| a11y | axe-core | ✅ |
| Prompt-injection regression | pytest | ✅ |
| E2E smoke | Playwright | ✅ on merge to main |
| Migration safety | sqlfluff lint + dry-run on shadow DB | ✅ |
| PR preview | Cloudflare Pages preview + HF Space preview branch | auto |
| Eval (nightly) | ragas + custom | regression > 2% blocks next deploy |

---

## §16 — Deployment & Release Strategy (NEW DETAIL)

**Cadence**:
- Frontend: every merge → preview → main (CDN, instant rollback)
- Backend: every merge → preview HF branch → main HF Space; emergency `KILL_SWITCH` env flag
- DB: forward-only by default; every migration ships with `down.sql`; tested on shadow DB before main applies

**Feature flags via PostHog** (gated rollout):
- `citation_mode_v2`, `groq_v_haiku`, `piper_voice_default`, `onboarding_coachmarks`, `tts_word_highlight`

**Canary**: HF Spaces lacks native canary. Substitute: PostHog flag `release_channel=canary` enabled for 10% of users; opt-in via `?channel=canary` URL.

---

## §17 — Monitoring + Observability (NEW DETAIL)

**SLOs**:
| SLI | Target | Window |
|---|---|---|
| RAG availability (warm, 2xx/total) | 99.5% | 30 days |
| RAG p95 latency, warm | ≤ 3s | 7 days |
| Indexing success rate | 98% | 7 days |
| TTS availability | 99% | 30 days |

**Alert thresholds → email + Discord webhook**:
- `/health` unreachable > 5 min
- Sentry error rate > 5/min for 10 min
- Supabase any-resource > 80%
- Groq error rate > 10% for 5 min
- Cost watermark: any provider > 70% of free tier for 24h

---

## §18 — Logging & Audit (NEW DETAIL)

**Retention**:
- App logs (HF Space stdout): 7 days
- `audit_log` table: 30 days (90 days for billing-adjacent events)
- `conversations`: 14 days (matches doc retention) unless user opts in

**Audit events**:
`auth.login`, `auth.logout`, `document.upload`, `document.delete`, `rag.ask`, `tts.synthesize`, `translate`, `admin.export`, `admin.delete_user`

**Sampling**: `rag.ask`, `tts.synthesize` sampled 10% in `audit_log`; full coverage in domain tables (`conversations`).

---

## §19 — Feedback Loop (NEW DETAIL)

| Loop | Trigger | Destination |
|---|---|---|
| Thumbs down on RAG answer | 👎 click | `conversations.user_rating = -1`; weekly review |
| "Wrong citation" flag | button | hard-negative captured for retrieval improvement |
| "Bad translation" flag | button | feeds BLEU regression set |
| "Report problem" | form | auto-files GitHub issue via `gh` in CI |

**Prompt iteration loop (weekly Friday)**:
1. Pull last week's thumbs-downs.
2. Categorize failures (retrieval / generation / citation / translation).
3. Propose ≤1 prompt change.
4. A/B on golden set via `eval/runners/prompt_compare.py`.
5. If win > 2%, promote, write ADR.

---

## §20 — Documentation (NEW DETAIL)

In addition to ARCHITECTURE / API / SECURITY / DEPLOY / RUNBOOK:
- `CONTRIBUTING.md` — code style, branch naming, PR template, ADR process
- `docs/adr/` — Architectural Decision Records (one per major decision; ~6 by Day 42)
- `docs/QUICKSTART.md` — 5-minute self-host guide
- `docs/glossary.md` — RAG, citation, chunk, embedding, etc.
- `docs/state-machines.md` — upload, RAG, TTS state diagrams
- `docs/ui-states.md` — empty/loading/error inventory
- `docs/SLOs.md` — formal SLOs + error budget calc

---

## §21 — Cost Management (NEW DETAIL)

(See §7 for tiers.)

**Per-user cost attribution**: nightly cron updates `user_usage_daily.cost_usd_estimate`. Top-10 spenders surfaced in admin dashboard.

**Budget-burn alerts** wired in §17.

**Cost dashboard**: PostHog dashboard pulling from `user_usage_daily` aggregated.

---

## §22 — Internationalization (NEW)

- **Library**: `react-i18next` (MIT)
- **Locales (priority)**: `en`, `hi`, `ta`, `bn`, `mr`, `te` — 6 priority. Other 8 of the 14 supported langs added v1.1 if traction.
- **Strings file**: `frontend/src/locales/{lang}.json` extracted Day 1
- **Detection**: browser `Accept-Language` → user setting → fallback `en`
- **RTL**: not needed v1; CSS `dir="auto"` set as a guard
- **Date/number formatting**: `Intl.DateTimeFormat` / `Intl.NumberFormat`, locale-aware
- **i18n in errors**: backend errors include a `code` (machine-readable), frontend renders the localized string

---

## §23 — Accessibility (NEW)

- **Target**: WCAG 2.1 AA
- **Keyboard nav**: every interactive element reachable + visible focus
- **Screen reader**: ARIA labels on all icon-only buttons; semantic HTML; live region (`role="status"`) for streaming RAG answer
- **Color contrast**: ≥ 4.5:1 for text; checked via axe-core in CI
- **Audio player**: keyboard shortcuts (Space=play/pause, ←/→=seek, ↑/↓=volume); transcript visible; no autoplay
- **Form errors**: announced via `role="alert"`
- **Skip link**: "skip to main content"
- **Manual test**: NVDA on Windows + VoiceOver on Mac before launch

---

## §24 — Disaster Recovery / Backups (NEW)

| Aspect | Target | Mechanism |
|---|---|---|
| RTO | 4 hours | Re-deploy from `main` + restore from R2 |
| RPO | 24 hours | Daily backup at 02:00 IST |
| Backup destination | Cloudflare R2 (free 10 GB) | Separate vendor from Supabase = real DR |
| What's backed up | `documents` (metadata only), `conversations`, `audit_log`, `prompts`, `users`, `user_usage_daily` | NOT chunk text/audio (regenerable) |
| Restore drill | Quarterly | `docs/RUNBOOK.md` § "DR drill" |
| Code | GitHub | DR-equivalent |

**Daily backup**: GitHub Actions cron (`0 20 * * *` UTC = 01:30 IST) runs `pg_dump` → S3-compatible put to R2.

---

## §25 — Capacity Planning (NEW)

**Watermarks → automated migration trigger**:
| Metric | Threshold | Action (auto-files GitHub issue) |
|---|---|---|
| Supabase DB usage | > 70% for 7 days | Migrate to Supabase Pro ($25/mo) |
| HF Spaces cold-start rate | > 10% sessions for 30 days | Migrate backend to Fly.io |
| Groq RPD | > 60% for 14 days | Add Haiku 4.5 fallback (~$5/mo) |
| Cloudflare R2 backups | > 50% (5 GB) | Add retention pruning beyond 30 days |
| Sentry events | > 60% mo for 2 mo | Upgrade to Team ($26/mo) |

Each trigger is a cron job that calls `gh issue create` with a templated migration playbook.

---

## §26 — Legal (NEW)

| Doc | Owner | Due | Notes |
|---|---|---|---|
| Terms of Service | you | Day 25 | Draft in `docs/legal/terms.md`; review with lawyer if traction |
| Privacy Policy | you | Day 25 | What's collected, retention, third parties (Groq, Supabase, HF, Cloudflare) |
| DMCA contact | you | Day 25 | Email + form in footer |
| India DPDP Act | you | rolling | Notice + consent UI, data principal rights, breach notification within 72h |
| GDPR (EU traffic) | you | when EU traffic detected | Same controls as DPDP cover most of GDPR |
| Cookie banner | you | Day 25 | Only if PostHog cookies used (we use anonymous distinctId; check) |

**Not for v1**: SOC 2, ISO 27001 — irrelevant at solo scale.

---

## §27 — Onboarding / First-Run UX (NEW)

- **Empty state on home**: "Drop a PDF or try our sample → [Bhagavad Gita Ch. 1] [NCERT Class 10 Math Sample]"
- **First upload tutorial**: 4-step coach-mark overlay (upload → wait → ask → cite)
- **"Try this question" chips** under empty chat input — generated from doc title via Groq
- **Welcome email** (Supabase Auth hook): explains 3 features in 60 seconds
- **Activation event in PostHog**: "first question with citation viewed" — north-star metric

---

## §28 — Build calendar (6 weeks)

> Phasing comes next — for now this is the day-by-day. Weeks 1–2 are foundation + RAG, 3–4 are polish + ops, 5–6 are hardening + launch. We'll group into phases after you sign off.

### Week 1 — Foundation, license-clean stack, i18n + a11y skeleton
| Day | Deliverable |
|---|---|
| 1 | Repo restructure. Apache-2.0 LICENSE. `.env.example`. Pin `pdfplumber, sentence-transformers, bge-m3, bge-reranker, groq, edge-tts, piper-tts, tenacity, pybreaker, react-i18next, axe-core`. Remove pymupdf, gemini-for-embeddings. AGPL-guard + gitleaks CI. **First ADR (stack).** **react-i18next setup with en+hi.** |
| 2 | Supabase: migrations + RLS + Storage + pg_cron. **`prompts`, `audit_log`, `idempotency_keys` tables.** HF Space + `/health`. Cloudflare Pages connected. |
| 3 | Auth (magic-link + Google OAuth). useAuth hook. JWT middleware. **audit_log writes for auth events.** |
| 4 | Upload endpoint with `Idempotency-Key` header. 50 MB + MIME + magic-byte validation. EXIF strip. |
| 5 | PDF text (pdfplumber) with bbox. OCR (Tesseract). FSM transitions. **Lang-detect on extracted text.** |
| 6 | Indic-aware chunking. **Boilerplate strip + Unicode NFC normalize + dedup.** Local bge-m3 with `embedding_model_version` stamping. HNSW. Chunk text → Storage. |
| 7 | E2E smoke. **Begin golden eval set on Kaggle (20 docs × 5 langs).** **First a11y baseline scan.** |

### Week 2 — RAG + Citation Mode + dogfood + state machines
| Day | Deliverable |
|---|---|
| 8 | `POST /rag/ask` SSE. Top-20 retrieve + reranker → top-5. **Tenacity retry budget + pybreaker circuit breaker for Groq.** |
| 9 | Structured Groq Llama 3.3 70B output. Citation validation. **Prompt v1 stored in `prompts` table.** |
| 10 | Frontend chat → backend. Delete client-side Gemini. SSE streaming. **RAG state machine implemented.** |
| 11 | Dual citation highlighting (char range + bbox overlay). |
| 12 | Translation pipeline + cache. Translate button rewired. |
| 13 | Prompt-injection guard. DOMPurify. CSP + HSTS. **Prompt-injection regression suite (30 known payloads).** |
| 14 | Integration tests. **Begin daily dogfood log.** **First contract test (schemathesis).** |

### Week 3 — TTS + UX states + a11y deep pass
| Day | Deliverable |
|---|---|
| 15 | edge-tts + Piper fallback unified `tts.synthesize()`. audio_cache. |
| 16 | `POST /tts` streams WAV. Frontend player. |
| 17 | Per-paragraph audio highlight. **Player keyboard shortcuts.** |
| 18 | slowapi rate limiting. user_usage_daily caps. KILL_SWITCH env. |
| 19 | **Empty / loading / error states on every fetch.** Error boundaries. Toasts. |
| 20 | **Delete `_legacy_gemini.ts`. Verify no client-side keys (grep VITE_*KEY).** |
| 21 | **a11y deep pass: keyboard nav, NVDA test, ARIA labels, focus management. Fix all axe-core blockers.** |

### Week 4 — Onboarding + DR + observability
| Day | Deliverable |
|---|---|
| 22 | Sentry @ 10% sample. PostHog events. **`docs/SLOs.md`.** |
| 23 | Eval harness: hit@5, citation precision, ragas faithfulness. Nightly Action. **Per-prompt eval runner.** |
| 24 | CI complete: pytest + Playwright + axe + license + secret scan + SBOM + migration safety. **PR preview envs.** |
| 25 | pg_cron 14-day cleanup. Export + delete endpoints. **Privacy + ToS + DMCA drafts published.** **Cookie banner.** |
| 26 | Security review pass: secret scan, npm/pip audit, CSP review, RLS verified by non-owner, **prompt-injection regression run.** |
| 27 | **Onboarding flow: sample PDFs, coach marks, "try this question" chips, welcome email.** |
| 28 | **DR setup: daily Supabase pg_dump → Cloudflare R2 via GitHub Actions cron.** Restore drill documented. |

### Week 5 — Hardening, capacity, alerts, retraining loops
| Day | Deliverable |
|---|---|
| 29 | **Alert rules wired: UptimeRobot + Sentry + Supabase webhooks → email + Discord.** |
| 30 | **Capacity watermarks + auto-issue cron** (DB%, HF cold rate, Groq RPD, R2 storage). |
| 31 | **Feedback loops: thumbs y/n, "wrong citation", "report problem" form → GitHub issues.** |
| 32 | **Hard-negative mining: weekly batch from feedback → retrieval eval set.** |
| 33 | **Prompt iteration loop: A/B runner; first prompt iteration cycle.** |
| 34 | **Load test (k6, 50 uploads + 200 queries/min) on staging. Fix bottlenecks.** |
| 35 | **Chaos test: simulate Groq 429, Supabase 503, HF cold start. Verify breakers + retries.** |

### Week 6 — Polish, docs, launch
| Day | Deliverable |
|---|---|
| 36 | **CONTRIBUTING.md, ~6 ADRs, QUICKSTART, glossary.** |
| 37 | Rewrite root README. Mobile responsive pass (360/768/1024/1440). |
| 38 | i18n: complete Hindi + Tamil + Bengali + Marathi + Telugu UI strings. |
| 39 | a11y final pass with NVDA + VoiceOver. |
| 40 | **Closed beta: 10 testers (classmates, friends, family). Watch Sentry + PostHog live.** |
| 41 | Triage + fix from beta feedback. |
| 42 | **Launch: r/IndiaTech, r/developersIndia, Show HN.** |

---

## §29 — Launch checklist (Day 42)

(Plan A's checklist + below.)
- [ ] axe-core a11y pass clean on top-5 pages
- [ ] Tested with NVDA screen reader
- [ ] WCAG 2.1 AA color contrast verified
- [ ] i18n complete for 6 priority languages
- [ ] Daily R2 backup runs verified; restore drill done
- [ ] All 6 capacity watermarks have automated alert rules
- [ ] Privacy / ToS / DMCA published
- [ ] India DPDP notice + consent live
- [ ] Cookie banner present (or absent if no cookies set)
- [ ] Prompt-injection regression suite green
- [ ] k6 load test green at 50 concurrent uploads
- [ ] 6+ ADRs published
- [ ] Idempotency keys verified on POST /documents
- [ ] Circuit breakers verified via chaos test
- [ ] Per-user cost attribution running

---

## §30 — What we cut to get to 4 weeks (if needed)

| Cut | Saves | Cost (carry to v1.1) |
|---|---|---|
| Skip Week 5 hardening (chaos + load tests, hard-negative mining, prompt iteration) | 7 days | Less robust under traffic; slower retrieval improvement loop |
| Skip i18n beyond en+hi | 2 days | Tamil/Bengali/Marathi/Telugu users see English UI |
| Skip ADRs + CONTRIBUTING | 1 day | Decision history rebuilt later from git |
| Skip welcome email + activation event | 1 day | Lower activation rate at launch |
| Skip mobile responsive | 1 day | Mobile users get desktop layout |

**Honest take:** keep the 6 weeks. Cutting Week 5 is the worst possible cut — the load+chaos tests find real bugs that hurt at launch.

---

## §31 — Open decisions

(Unchanged from Plan A.)
1. Domain — `ariareads.in` / `readaria.app` / Cloudflare subdomain?
2. UI default lang — English-first with Hindi toggle, or Hindi-first?
3. Telemetry — opt-in or opt-out? (DPDP leans opt-in.)

Reply with answers + the phase split (next step) and I start Day 1.

---

## §32 — Next step: phase split

Once you sign off on this plan, I'll propose a phase split — likely:

| Phase | Weeks | Goal | Exit criterion |
|---|---|---|---|
| **Phase 1 — Foundation** | 1 | Repo + auth + storage + ingestion pipeline | First doc indexed end-to-end |
| **Phase 2 — Core RAG + Citation** | 2 | Question → cited answer working | hit@5 ≥ 70% on 1 doc |
| **Phase 3 — Audio + Polish** | 3 | TTS + a11y + UX states | Internal dogfood survives 1 hour of use |
| **Phase 4 — Production Ops** | 4 | Observability + DR + onboarding | Eval gate green; alerts wired |
| **Phase 5 — Hardening** | 5 | Chaos + load + feedback loops | Survives k6 50-concurrent test |
| **Phase 6 — Launch** | 6 | Docs + closed beta + Show HN | 10 beta testers, Sentry clean |

Confirm or adjust when you reply.
