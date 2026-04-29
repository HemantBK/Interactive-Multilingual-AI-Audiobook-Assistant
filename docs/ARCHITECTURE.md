# Architecture

The authoritative plan is [`build plan.md`](../build%20plan.md).
This page is the **evergreen** view — the plan freezes at v1 launch, this
file moves with the code.

Diagrams use [Mermaid](https://mermaid.js.org). GitHub renders them inline
in the browser; in your IDE install the Mermaid preview extension.

---

## 1. System context

```mermaid
flowchart LR
    user([User])
    subgraph cf[Cloudflare Pages]
        spa[React SPA<br/>Vite + Tailwind]
    end
    subgraph hf[HF Spaces - Docker]
        api[FastAPI 3.11<br/>backend]
    end
    subgraph sb[Supabase ap-south-1]
        pg[(Postgres<br/>+ pgvector)]
        auth[Auth]
        st[(Storage)]
    end
    subgraph cpu[Local CPU - in container]
        bge1[bge-m3<br/>embed]
        bge2[bge-reranker-v2-m3]
        tess[Tesseract]
        piper[Piper TTS<br/>fallback]
    end
    groq[Groq API<br/>Llama 3.3 70B]
    edge[Edge-TTS<br/>Microsoft]
    sentry[Sentry]
    posthog[PostHog]
    r2[(Cloudflare R2<br/>backups)]

    user -- HTTPS<br/>JWT --> spa
    spa -- HTTPS<br/>Bearer JWT --> api
    spa -. magic link / OAuth .-> auth
    spa -. signed URLs .-> st
    api --> pg
    api --> auth
    api --> st
    api --> bge1
    api --> bge2
    api --> tess
    api --> piper
    api -- prompts + chunks --> groq
    api -- text --> edge
    spa -- traces 10% .-> sentry
    api -- traces 10% .-> sentry
    spa -- events post-consent .-> posthog
    pg -- daily pg_dump cron --> r2
```

### Trust boundary (one rule)

**The browser never holds a third-party API key.** All Groq / Gemini /
Edge-TTS / Sentry-DSN / PostHog-key are bundled or server-side; the
browser only ever has Supabase URL + anon key + the user's Supabase JWT.
CI's `no-client-side-ai` job (Day 20) blocks regressions.

---

## 2. Upload + indexing flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User (browser)
    participant API as FastAPI
    participant DB as Supabase Postgres
    participant ST as Supabase Storage
    participant TS as Tesseract / pdfplumber
    participant EM as bge-m3

    U->>API: POST /documents (file, title, Idempotency-Key)
    API->>API: validate (size, MIME, magic bytes, EXIF strip if image)
    API->>API: hash = sha256(bytes + title + user_id)
    API->>DB: idempotency_keys lookup
    alt cache hit
        DB-->>API: existing response
        API-->>U: 201 (cached)
    else cache miss
        API->>API: doc_id = uuid5(NS, user_id|key)
        API->>ST: upload <user_id>/<doc_id>/original.<ext>
        API->>DB: upsert documents (status='queued')
        API->>DB: idempotency_keys.insert
        API->>API: write_audit document.upload
        API-->>U: 201 (queued)
        API->>API: BackgroundTasks.add_task(run_indexing)
        Note over API: returns to client<br/>indexing happens asynchronously
        API->>DB: documents.status = 'processing'
        API->>ST: download original.<ext>
        API->>TS: extract → pages[].text + words[].bbox
        API->>API: preprocess (NFC, boilerplate strip, dedup)
        API->>API: chunk (Indic separators, 500/50)
        API->>EM: embed chunk_texts → 1024-d vectors
        API->>ST: upload chunks/<doc_id>/chunks.json (all chunk texts)
        API->>DB: insert document_chunks (1024-d halfvec, bbox)
        API->>DB: documents.status = 'ready'
    end
```

---

## 3. RAG (ask-with-citation) flow

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant API as FastAPI
    participant EM as bge-m3
    participant DB as Postgres + pgvector
    participant ST as Storage (chunks)
    participant RR as bge-reranker-v2-m3
    participant LLM as Groq Llama 3.3 70B

    U->>API: POST /rag/ask (document_id, question)
    API->>DB: select status from documents
    alt not 'ready'
        API-->>U: 409
    else ready
        API->>API: quotas.assert_under_cap('rag_queries')
        API->>API: write_audit rag.ask
        API->>API: quotas.bump
        Note over API: SSE: data: {"event":"start"}
        API->>EM: embed(question) → 1024-d
        API->>DB: rpc search_chunks → top-20 by HNSW cosine
        API->>ST: download chunks/<doc>/chunks.json (one round-trip)
        API->>RR: rerank top-20 → top-5
        API->>LLM: prompt = system + <chunks id="..">+ question<br/>response_format=json_object
        loop streaming
            LLM-->>API: token
        end
        API->>API: parse JSON {answer, citations}
        API->>API: validate_citations (chunk_id ∈ set, quote ⊆ chunk.text)
        API->>API: filter_answer (drop credentials/scripts)
        API->>DB: insert into conversations<br/>(latency, tokens, cited_chunks[])
        API-->>U: data: {"event":"answer", answer, citations}
        API-->>U: data: {"event":"done", retrieved_chunks, latency_ms}
    end
```

---

## 4. Data model (top-level)

```mermaid
erDiagram
    auth_users ||--o{ documents : owns
    documents ||--o{ document_chunks : has
    documents ||--o{ conversations : has
    documents ||--o| documents_keepalive : opt_in
    auth_users ||--o{ conversations : asks
    auth_users ||--o{ user_usage_daily : counts
    auth_users ||--o{ audit_log : actions
    auth_users ||--o{ idempotency_keys : keys
    audio_cache }|..|| documents : referenced_by
    translation_cache }|..|| documents : referenced_by
    prompts ||--o{ conversations : powered

    documents {
        uuid id PK
        uuid user_id FK
        text title
        text source_type "pdf|image|text"
        text status "queued|processing|ready|failed"
        text storage_path
        int page_count
        text source_language
        timestamptz created_at
    }
    document_chunks {
        bigserial id PK
        uuid document_id FK
        int chunk_index
        text text_storage_path
        int page_number
        int char_start
        int char_end
        jsonb bbox
        halfvec_1024 embedding
        text embedding_model_version
        text lang_detect
    }
    conversations {
        uuid id PK
        uuid document_id FK
        uuid user_id FK
        text question
        text answer
        bigint_array cited_chunks
        int latency_ms
        int tokens_in
        int tokens_out
    }
    audit_log {
        bigserial id PK
        uuid user_id
        text action
        jsonb metadata "redacted"
        text ip_hash "sha256(ip||today)"
    }
    prompts {
        text id PK1
        int version PK2
        text content
        boolean is_active "unique per id"
    }
```

Full DDL: [`infra/supabase/migrations/0001_initial_schema.sql`](../infra/supabase/migrations/0001_initial_schema.sql).

---

## 5. Reliability layers (Groq path)

```mermaid
flowchart TD
    caller[stream_rag_answer] --> client[groq_stream_chat]
    client --> cb{AsyncCircuitBreaker<br/>fail_threshold=5<br/>reset=60s}
    cb -- closed --> retry[tenacity @retry<br/>3 attempts, 0.5/1/2s exp]
    cb -- open --> short[GroqUnavailableError]
    retry -- transient --> create[AsyncGroq.chat...create<br/>timeout=30s]
    retry -- 4xx --> fail[no retry<br/>surface as GroqUnavailableError]
    create -- success --> stream[iterate stream<br/>NO retry mid-stream]
    stream --> done[SSE event: answer]
```

Same pattern wraps `/translate` and the citation-judge path in eval.

---

## 6. Operational invariants (do not break)

- **No third-party API keys in the frontend bundle** — backend proxies everything.
- **Every chunk stores citation anchors** (`page_number`, `char_start`, `char_end`, `bbox`). Citation Mode depends on these.
- **Every user-facing table has Row-Level Security enabled.** Backend uses `user_client(JWT)` for user data, `admin_client()` only for backend-owned tables.
- **Caches are content-addressable** (sha256 of inputs). Never key on user IDs.
- **Rate limits enforced server-side** (slowapi per-IP) AND user-side (`user_usage_daily` quotas) even if the client forgets.
- **Idempotency keys on `POST /documents`** — replays converge on the same `doc_id`.
- **Audit row written BEFORE destructive actions** (delete account, prompt swap) so the trail survives the action.

---

## 7. Where to look next

| Want to know… | Go to |
|---|---|
| Why we chose Groq over Gemini | [adr/0001-stack-choice.md](adr/0001-stack-choice.md) §Decision |
| What runs in CI | [DEPLOY.md](DEPLOY.md) §CI gates |
| What pages, on whom | [SLOs.md](SLOs.md) §Alert routing |
| How to recover from a Sentry-pageworthy outage | [RUNBOOK.md](RUNBOOK.md) |
| What the `chunks` bucket layout looks like | this file §2 + `infra/supabase/migrations/0001_initial_schema.sql` |
