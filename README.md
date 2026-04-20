# ARIA

**Automated Reading Interactive Assistant** — a multilingual AI reader for books, PDFs, and images with **precise citations**, native-quality Indic voices, and an interactive Q&A companion.

> **Status:** v1 under construction. See [`PLAN.md`](./PLAN.md) for the 4-week build plan and [`CHANGELOG.md`](./CHANGELOG.md) for what shipped. License: Apache-2.0.

## What it does

- Upload any PDF, image, or text file (≤ 50 MB)
- Extract text (Tesseract OCR with Gemini Vision fallback)
- Narrate in **14 languages** with free, native-quality voices (Edge-TTS)
- Translate between all 14 languages
- Ask questions in natural language — every answer highlights the **exact source paragraph** with page + character-level citations

## Why it exists

Mainstream readers (NotebookLM, Speechify, ElevenLabs Reader) handle English beautifully but treat Indic languages as an afterthought. ARIA flips that: the core app is general-purpose, but **Hindi, Bengali, Marathi, Tamil, Telugu** are first-class from day one. The differentiator is **Citation Mode** — every claim in a model's answer is anchored to the exact paragraph in your source so you can verify without leaving the page.

## Stack (all free-tier)

| Layer | Tech |
|---|---|
| Frontend | React 19 + Vite + Tailwind → Cloudflare Pages |
| Backend | FastAPI (Python 3.11) → Hugging Face Spaces (Docker) |
| Database + Auth + Storage + Vectors | Supabase (Postgres + pgvector) |
| OCR | Tesseract (primary), Gemini Vision (fallback) |
| TTS | edge-tts (400+ voices, native Indic) |
| LLM | Gemini 2.5 Flash, Groq Llama fallback |
| Embeddings | Gemini `text-embedding-004` (768-dim), `bge-m3` local fallback |
| CI | GitHub Actions |

Full architecture: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md).
Security model: [`docs/SECURITY.md`](./docs/SECURITY.md).
Deploy guide: [`docs/DEPLOY.md`](./docs/DEPLOY.md).

## Repository layout

```
.
├── frontend/     # React SPA → Cloudflare Pages
├── backend/      # FastAPI → Hugging Face Spaces
├── infra/        # Supabase migrations, HF Space config, Cloudflare headers
├── eval/         # RAG quality harness
├── docs/         # Architecture, security, deploy, runbook
├── memory/       # Session memory (not deployed)
├── PLAN.md       # 4-week v1 build plan
├── CHANGELOG.md
└── LICENSE       # Apache-2.0
```

## Local development

```bash
# frontend
cd frontend
npm install
npm run dev              # http://localhost:5173

# backend (separate terminal)
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env
# edit ../.env with Supabase + Gemini keys
uvicorn app.main:app --reload --port 7860
```

Then open http://localhost:5173.

## Contributing

This project is in active early development. If you want to contribute, open an issue first so we can align on scope.

## License

[Apache License 2.0](./LICENSE). Includes a patent grant — safe for commercial use with attribution.

## Contact

Security reports → `hemantkumar.bk@gmail.com` with subject `SECURITY`. See [`docs/SECURITY.md`](./docs/SECURITY.md).
