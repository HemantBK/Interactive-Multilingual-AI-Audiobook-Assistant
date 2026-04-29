# Interactive Audiobook-Assistant

Multilingual AI reader for books, PDFs, and images with **precise citations**, native-quality Indic voices, and a free-at-v1-scale stack.

> Status: v1 in build (~ Phase 4 / 6). Active plan: [`build plan.md`](./build%20plan.md). Shipped artefacts: [`CHANGELOG.md`](./CHANGELOG.md). License: Apache-2.0.

## Why

Mainstream readers (NotebookLM, Speechify, ElevenLabs Reader) treat Indic
languages as an afterthought. We flip that: general-purpose product,
**Hindi / Bengali / Marathi / Tamil / Telugu first-class**, **Citation Mode**
(every answer pinned to the exact source paragraph) as the moat.

## What it does

- Upload any **PDF / image / text file** (≤ 50 MB)
- Extract text — Tesseract OCR primary, Gemini Vision fallback (paid only)
- Ask questions — Groq Llama 3.3 70B; every answer cites the exact passage
- Translate — between 14 languages, content-addressable cache
- Narrate — Edge-TTS (Piper fallback), per-paragraph highlight, keyboard map

## 60-second quickstart

```bash
git clone <repo-url> audiobook-assistant && cd audiobook-assistant
cp .env.example .env   # fill in Supabase + Groq keys

# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

Full guide: [`docs/QUICKSTART.md`](docs/QUICKSTART.md).

## Documentation

```
README.md           ← you are here
build plan.md       ← active 6-week build plan
CHANGELOG.md        ← shipped per day

docs/
├── INDEX.md           ← all docs by audience (start here for the deep dive)
├── QUICKSTART.md      ← run locally in 5 minutes
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

## Stack (one-line summary)

React 19 + Vite + Tailwind on **Cloudflare Pages**, FastAPI 3.11 on
**Hugging Face Spaces (Docker)**, Postgres + pgvector + Auth + Storage on
**Supabase**, **Groq Llama 3.3 70B** for RAG + translate, **bge-m3** local
embeddings, **bge-reranker-v2-m3** local rerank, **edge-tts + Piper** for
voice. License-clean (Apache-2.0; CI blocks AGPL/SSPL).

Full table with rationale: [`docs/adr/0001-stack-choice.md`](docs/adr/0001-stack-choice.md).

## License

[Apache 2.0](./LICENSE). Patent grant included.

## Security & contact

Vulnerabilities → `hemantkumar.bk@gmail.com`, subject `SECURITY`.
General issues → GitHub Issues.
