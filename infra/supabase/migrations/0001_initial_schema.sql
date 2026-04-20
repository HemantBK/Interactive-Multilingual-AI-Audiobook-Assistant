-- ============================================================================
-- ARIA — Initial Schema (v1 Day 1)
-- Run via Supabase SQL editor or `supabase db push`.
-- Row-Level Security is ENABLED on every user-facing table.
-- ============================================================================

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists vector;

-- ----------------------------------------------------------------------------
-- documents: one row per user upload
-- ----------------------------------------------------------------------------
create table if not exists public.documents (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references auth.users(id) on delete cascade,
    title           text not null,
    source_type     text not null check (source_type in ('pdf','image','text')),
    storage_path    text not null,
    page_count      int,
    source_language text,
    status          text not null check (status in ('uploading','processing','ready','failed')),
    error_message   text,
    created_at      timestamptz not null default now(),
    processed_at    timestamptz
);
create index if not exists idx_documents_user_id on public.documents(user_id);
create index if not exists idx_documents_status  on public.documents(status);

alter table public.documents enable row level security;

create policy "users read own documents"
    on public.documents for select
    using (auth.uid() = user_id);

create policy "users insert own documents"
    on public.documents for insert
    with check (auth.uid() = user_id);

create policy "users update own documents"
    on public.documents for update
    using (auth.uid() = user_id);

create policy "users delete own documents"
    on public.documents for delete
    using (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- document_chunks: indexed units with citation anchors (page, char offsets)
-- halfvec(768) = half-precision embeddings, ~50% storage vs float4
-- ----------------------------------------------------------------------------
create table if not exists public.document_chunks (
    id            bigserial primary key,
    document_id   uuid not null references public.documents(id) on delete cascade,
    chunk_index   int not null,
    text          text not null,
    page_number   int not null,
    char_start    int not null,
    char_end      int not null,
    token_count   int,
    embedding     halfvec(768),
    created_at    timestamptz not null default now()
);
create index if not exists idx_chunks_document_id on public.document_chunks(document_id);
-- HNSW index for fast cosine similarity search
create index if not exists idx_chunks_embedding_hnsw
    on public.document_chunks
    using hnsw (embedding halfvec_cosine_ops);

alter table public.document_chunks enable row level security;

-- Users can only see chunks of documents they own
create policy "users read own chunks"
    on public.document_chunks for select
    using (
        exists (
            select 1 from public.documents d
            where d.id = document_chunks.document_id
              and d.user_id = auth.uid()
        )
    );

-- ----------------------------------------------------------------------------
-- audio_cache: content-addressable TTS cache
-- ----------------------------------------------------------------------------
create table if not exists public.audio_cache (
    content_hash      text primary key,        -- sha256(text|voice|language)
    voice             text not null,
    language          text not null,
    storage_path      text not null,           -- key in Supabase Storage
    duration_sec      numeric,
    size_bytes        bigint,
    hit_count         int not null default 0,
    created_at        timestamptz not null default now(),
    last_accessed_at  timestamptz not null default now()
);
-- No RLS: global cache, accessed only from backend (service role).

-- ----------------------------------------------------------------------------
-- translation_cache: content-addressable translation cache
-- ----------------------------------------------------------------------------
create table if not exists public.translation_cache (
    content_hash       text primary key,        -- sha256(text|target_lang)
    source_language    text,
    target_language    text not null,
    translated_text    text not null,
    hit_count          int not null default 0,
    created_at         timestamptz not null default now()
);
-- No RLS: backend-only writes, backend-mediated reads.

-- ----------------------------------------------------------------------------
-- conversations: Q/A history + feedback + audit
-- ----------------------------------------------------------------------------
create table if not exists public.conversations (
    id             uuid primary key default uuid_generate_v4(),
    document_id    uuid not null references public.documents(id) on delete cascade,
    user_id        uuid references auth.users(id) on delete set null,
    question       text not null,
    answer         text not null,
    cited_chunks   bigint[] not null default '{}',
    latency_ms     int,
    tokens_in      int,
    tokens_out     int,
    model          text,
    user_rating    smallint check (user_rating in (-1, 0, 1)) default 0,
    created_at     timestamptz not null default now()
);
create index if not exists idx_conversations_document_id on public.conversations(document_id);
create index if not exists idx_conversations_user_id     on public.conversations(user_id);

alter table public.conversations enable row level security;

create policy "users read own conversations"
    on public.conversations for select
    using (auth.uid() = user_id);

create policy "users insert own conversations"
    on public.conversations for insert
    with check (auth.uid() = user_id);

create policy "users update own conversations"
    on public.conversations for update
    using (auth.uid() = user_id);

-- ----------------------------------------------------------------------------
-- user_usage_daily: per-user per-day counters for rate limiting + billing
-- ----------------------------------------------------------------------------
create table if not exists public.user_usage_daily (
    user_id             uuid not null,
    date                date not null,
    documents_uploaded  int not null default 0,
    pages_processed     int not null default 0,
    tts_chars           int not null default 0,
    rag_queries         int not null default 0,
    primary key (user_id, date)
);

alter table public.user_usage_daily enable row level security;

create policy "users read own usage"
    on public.user_usage_daily for select
    using (auth.uid() = user_id);
