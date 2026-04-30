# ARIA — Multilingual AI Reader with Citation Mode

[![CI](https://github.com/HemantBK/Interactive-Multilingual-AI-Audiobook-Assistant/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/HemantBK/Interactive-Multilingual-AI-Audiobook-Assistant/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/HemantBK/Interactive-Multilingual-AI-Audiobook-Assistant)](https://github.com/HemantBK/Interactive-Multilingual-AI-Audiobook-Assistant/commits/main)
[![Tests](https://img.shields.io/badge/tests-203_backend_%C2%B7_6_e2e_%C2%B7_axe--a11y-brightgreen)](#tests--ci)
[![Indic](https://img.shields.io/badge/Indic-first-orange)](#why)

> Upload a PDF, image, or text file. Ask questions in any language.
> Every answer is pinned to the exact source paragraph. Built Indic-first.

<!--
  TODO (high priority): replace this comment with a 10-second hero GIF or
  screenshot showing the citation jump (Q&A → click citation → PDF
  highlights the source passage). Recommended path: docs/assets/hero.gif
  (≤ 5 MB so it stays inline on GitHub).

  ![ARIA — citation jump demo](docs/assets/hero.gif)
-->

**203 backend tests · 6 Playwright e2e · axe-core a11y · 13 CI jobs** — all green on `main`.
Apache-2.0, zero AGPL/SSPL deps (CI-enforced).

> **Status:** v1 in build (~ Phase 4 / 6). Active plan: [`build plan.md`](./build%20plan.md). Shipped artefacts: [`CHANGELOG.md`](./CHANGELOG.md).

---

## Why

Mainstream readers (NotebookLM, Speechify, ElevenLabs Reader) treat Indic
languages as an afterthought. ARIA flips that: general-purpose reader,
**Hindi / Bengali / Marathi / Tamil / Telugu first-class**, **Citation Mode**
(every answer pinned to the exact source paragraph) as the moat.

## What it does

- **Upload** PDF, image, or text (≤ 50 MB)
- **Extract** — pdfplumber for digital PDFs, Tesseract OCR for scanned/image input, Gemini Vision as paid fallback
- **Ask** — Groq Llama 3.3 70B; every answer cites the exact passage with chunk ID and bounding box
- **Translate** — between 14 languages, content-addressable cache (free re-reads)
- **Narrate** — Edge-TTS native voices (Piper fallback), per-paragraph highlight, keyboard-mapped controls

## Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React 19 + Vite + Tailwind | Modern, fast HMR |
| Frontend host | Cloudflare Pages | Free at v1 scale, edge SSL |
| Backend | FastAPI 0.120 (Python 3.11) | Async, OpenAPI 3.1 out of the box |
| Backend host | Hugging Face Spaces (Docker) | Free CPU tier, persistent storage |
| Database | Postgres + pgvector (Supabase) | RLS for free, `halfvec` 1024-dim embeddings |
| Auth + Storage | Supabase Auth + Storage | Single platform, free tier |
| LLM | Groq Llama 3.3 70B | Free tier, ~500 tok/s |
| Embeddings | bge-m3 (1024-dim) | Indic-strong, runs on CPU |
| Reranker | bge-reranker-v2-m3 | Local, license-clean |
| TTS | edge-tts (primary) + Piper (fallback) | Native Indic voices, license-clean fallback |
| Observability | Sentry + PostHog | Free tier, GDPR/DPDP-aligned |

License-clean: CI fails the build on AGPL / SSPL / Commons-Clause deps.
Full rationale per choice: [`docs/adr/0001-stack-choice.md`](docs/adr/0001-stack-choice.md).

## Try it

- **Live demo:** _coming soon_ — Hugging Face Space + Cloudflare Pages (both free tier)
- **Run locally:** [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — requires a free Supabase project + Groq API key (no credit card)

## Documentation

Audience-segmented entry points: [`docs/INDEX.md`](docs/INDEX.md).

```
README.md           ← you are here
build plan.md       ← active 6-week build plan
CHANGELOG.md        ← shipped per phase

docs/
├── INDEX.md           ← all docs by audience
├── QUICKSTART.md      ← run locally
├── ARCHITECTURE.md    ← system diagrams, sequence flows, data model
├── DEPLOY.md          ← CI gates, environments, rollback
├── RUNBOOK.md         ← incidents + common ops
├── SECURITY.md        ← threat model, vuln reporting
├── SLOs.md            ← service-level objectives + error budgets
├── CONTRIBUTING.md    ← branching, PR checks, ADR process
├── ui-states.md       ← every fetch's empty/loading/error state
├── a11y-test-plan.md  ← NVDA / VoiceOver / axe-core checklist
├── glossary.md        ← RAG, citation, chunk, embedding, …
├── dogfood-log.md     ← daily issue tracking during build
├── adr/               ← architectural decision records
├── legal/             ← privacy, terms, DMCA
└── security/          ← audit reviews, RLS verification runbook
```

## Tests & CI

13 jobs run on every push and PR. The full matrix:

| Job | Tool | Gates |
|---|---|---|
| `backend-tests` | pytest 9 | 203 unit + contract tests |
| `backend-lint` | ruff 0.7 | Style + bugs (`E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`, `S`) |
| `typecheck-frontend` | tsc 5.8 | Strict TypeScript |
| `lint-frontend` | eslint 9 + prettier 3 | Style + format |
| `e2e-and-a11y` | Playwright + axe-core | 6 e2e + a11y rules |
| `migration-safety` | psql shadow DB | All Supabase migrations apply cleanly |
| `pip-audit` | pip-audit 2.7 | Zero Python CVEs |
| `npm-audit` | npm audit | Zero high+ npm CVEs |
| `license-guard-backend` | pip-licenses | No AGPL / SSPL / Commons-Clause |
| `license-guard-frontend` | license-checker | No AGPL / SSPL / Commons-Clause |
| `secret-scan` | gitleaks | No leaked credentials in history |
| `no-client-side-ai` | grep guard | No AI SDKs / keys in browser bundle |
| `sbom` | anchore/syft | SPDX SBOM artefact every build |

Run the full backend suite locally:

```bash
cd backend && pytest -m 'not integration'   # ~90 s, 203 tests
```

## License

[Apache 2.0](./LICENSE) — patent grant included.

## Security & contact

Vulnerabilities → `hemantkumar.bk@gmail.com`, subject `SECURITY` (response within 72 h).
General issues → [GitHub Issues](https://github.com/HemantBK/Interactive-Multilingual-AI-Audiobook-Assistant/issues).
