# Architecture

The authoritative reference is [`PLAN.md`](../PLAN.md). This page is the evergreen version — `PLAN.md` is a point-in-time plan for v1, this is kept in sync with reality as the system evolves.

## Shape (current)

```
[Browser]
   │
   ├── React SPA (Cloudflare Pages)
   │     └── talks ONLY to our FastAPI backend (never to Gemini directly)
   │
   ▼
[FastAPI backend — Hugging Face Spaces]
   ├── Supabase (Postgres + pgvector + Auth + Storage)
   ├── Gemini API (OCR vision fallback, translation, RAG LLM)
   ├── Edge-TTS (narration, 14 languages)
   └── Tesseract (local OCR, primary path)
```

## Invariants (do not break)

- **No third-party API keys in the frontend bundle.** All external calls proxied by backend.
- **Every chunk stores citation anchors** (`page_number`, `char_start`, `char_end`). Citation Mode depends on these.
- **Every table with user data has Row-Level Security enabled.**
- **Caches are content-addressable** (sha256 over inputs). Never key on user IDs.
- **Rate limits are enforced server-side** even if the client forgets.

## Request-flow details

See `PLAN.md §2` for upload and RAG flows.

## Data model

See `infra/supabase/migrations/0001_initial_schema.sql`.
