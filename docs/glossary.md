# Glossary

Terms used across ARIA's docs + code.

| Term | Meaning |
|---|---|
| **bbox** | Bounding box. `{page, x0, y0, x1, y1}` rectangle for a word or chunk. PDF coords are in points (1/72 inch); image coords are in pixels. Origin top-left in both. |
| **bge-m3** | `BAAI/bge-m3`. Multilingual sentence-transformer that produces 1024-dim embeddings. Strong on Indic languages. Runs locally on CPU. |
| **bge-reranker-v2-m3** | Cross-encoder version of bge-m3. Re-scores (question, chunk) pairs after a cheap retrieval pass. ~150 ms / batch. |
| **Citation Mode** | The product moat. Every RAG answer is paired with `chunk_id` + verbatim `quote` that maps to a `page_number` + `bbox` in the source. Click to jump. |
| **chunk** | A 500-character substring of a document, with citation anchors (`page_number`, `char_start`, `char_end`, `bbox`). Stored as a row in `document_chunks` with a 1024-dim embedding. |
| **circuit breaker** | Pattern that stops calling a sick upstream after N consecutive failures. Reopens for one trial after a cooldown. Implemented in `app/services/circuit_breaker.py`. |
| **content_hash** | `sha256(text + voice + lang)` (TTS) or `sha256(text + target_lang)` (translate) or `sha256(file + title + user_id)` (idempotency). Cache key. |
| **DPDP** | Digital Personal Data Protection Act, India 2023. Defines data principal rights (access, correction, erasure), grievance officer, breach notice within 72h. |
| **edge-tts** | Reverse-engineered Microsoft Edge TTS. Free, no SLA. Used as primary voice provider; Piper is the fallback. |
| **error budget** | `1 - SLO target` over a window. 99.5% / 30 days = 3h 36min of allowed downtime. Spend it = freeze new features. See [SLOs.md](SLOs.md). |
| **FSM** | Finite State Machine. Documents transition `queued → processing → ready | failed`; the RAG state machine is `idle → asking → streaming → done | error`. |
| **golden set** | The hand-labeled Q/A + expected-citation pairs in `eval/datasets/golden_set.json`. Day 23 eval harness scores against it nightly. |
| **halfvec** | pgvector half-precision (16-bit) vector type. `halfvec(1024)` = 2 KB per row vs 4 KB for float4. |
| **HNSW** | Hierarchical Navigable Small World — pgvector's approximate-nearest-neighbour index. Sub-linear search; tunable accuracy. |
| **idempotency key** | UUID provided by the client on `POST /documents`. Same key + same body → same response (cached). Same key + different body → 409. |
| **kill switch** | Env-flag (`KILL_SWITCH=true`) middleware that returns 503 on every AI / mutation endpoint. Operator emergency stop. |
| **MRR** | Mean Reciprocal Rank. Average of `1/position` of the first relevant chunk in retrieval results. Tier-2 SLO. |
| **NFC** | Unicode Normalization Form C — compose. Run on extracted text before chunking so "क़" (precomposed) and "क़" (decomposed) hash the same. |
| **pg_cron** | Postgres extension that schedules SQL on a cron expression. Runs the 14-day document cleanup, audit_log retention, idempotency-key TTL. |
| **pgvector** | Postgres extension adding vector column types + ANN indexes (HNSW, IVFFLAT). Powers retrieval. |
| **prompt registry** | `public.prompts` table; `(id, version)` PK with a unique `is_active` index per id. Day 33's iteration loop A/Bs new versions before flipping the active flag. |
| **PostHog** | Product analytics SaaS. Used post-consent only. Stores distinct_id in localStorage (no cookies). |
| **RAG** | Retrieval-Augmented Generation. Embed question → search vector index → rerank → prompt the LLM with retrieved chunks. |
| **ragas** | Eval framework for RAG. Provides `Faithfulness` (does the answer use only the retrieved context) + others. Used in `eval/runners/answer_eval.py`. |
| **RLS** | Row-Level Security. Postgres policies that filter rows by predicates derived from the JWT (`auth.uid()`). User A can never see User B's rows even with a buggy backend query. |
| **RPO / RTO** | Recovery Point Objective (acceptable data loss) / Recovery Time Objective (acceptable downtime). v1 targets: RPO 24h, RTO 4h. |
| **search_chunks** | Postgres RPC defined in `0003_search_chunks_fn.sql`. `(document_id, query_embedding, k) → top-k chunks by cosine similarity`. `security invoker` → RLS still applies. |
| **Sentry** | Error + performance SaaS. 10% trace sample, 100% error capture; PII off. |
| **SLI / SLO** | Service Level Indicator (the metric) / Service Level Objective (the promise). 4 Tier-1 SLOs in [SLOs.md](SLOs.md). |
| **slowapi** | FastAPI rate-limiter. Per-IP via `X-Forwarded-For`-aware key function. |
| **tenacity** | Python retry library. Wraps `groq_stream_chat`'s connect step. |
