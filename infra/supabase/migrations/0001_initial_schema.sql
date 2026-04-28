-- =============================================================================
-- ARIA — Initial Schema (build plan A2, Day 2)
-- Run via Supabase SQL editor or `supabase db push`.
-- Row-Level Security is ENABLED on every user-facing table.
--
-- This is the consolidated initial migration. Subsequent migrations land in
-- 0002_*.sql onward and MUST ship with a `down` block (A2 §16).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists vector;

-- =============================================================================
-- documents — one row per user upload
-- =============================================================================
create table if not exists public.documents (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references auth.users(id) on delete cascade,
    title           text not null,
    source_type     text not null check (source_type in ('pdf','image','text')),
    storage_path    text not null,
    page_count      int,
    source_language text,
    status          text not null check (status in ('queued','uploading','processing','ready','failed')),
    error_message   text,
    created_at      timestamptz not null default now(),
    processed_at    timestamptz
);
create index if not exists idx_documents_user_id on public.documents(user_id);
create index if not exists idx_documents_status  on public.documents(status);
create index if not exists idx_documents_created_at on public.documents(created_at);

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

-- =============================================================================
-- documents_keepalive — opt-in flag, doc survives 14-day cleanup if present
-- =============================================================================
create table if not exists public.documents_keepalive (
    document_id  uuid primary key references public.documents(id) on delete cascade,
    user_id      uuid not null,
    created_at   timestamptz not null default now()
);
create index if not exists idx_keepalive_user_id on public.documents_keepalive(user_id);

alter table public.documents_keepalive enable row level security;

create policy "users manage own keepalives"
    on public.documents_keepalive for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- =============================================================================
-- document_chunks — citation anchors + bounding boxes; text in Storage
-- halfvec(1024) = bge-m3 native dim, half-precision (~50% storage vs float4)
-- =============================================================================
create table if not exists public.document_chunks (
    id                       bigserial primary key,
    document_id              uuid not null references public.documents(id) on delete cascade,
    chunk_index              int not null,
    text_storage_path        text not null,                -- chunk text in Supabase Storage, NOT inline
    page_number              int not null,
    char_start               int not null,
    char_end                 int not null,
    bbox                     jsonb,                        -- [{page,x0,y0,x1,y1}] for in-PDF highlight
    token_count              int,
    embedding                halfvec(1024),
    embedding_model_version  text not null default 'bge-m3@1.0',
    lang_detect              text,
    created_at               timestamptz not null default now()
);
create index if not exists idx_chunks_document_id on public.document_chunks(document_id);
create index if not exists idx_chunks_embedding_hnsw
    on public.document_chunks
    using hnsw (embedding halfvec_cosine_ops);

alter table public.document_chunks enable row level security;

create policy "users read own chunks"
    on public.document_chunks for select
    using (
        exists (
            select 1 from public.documents d
            where d.id = document_chunks.document_id
              and d.user_id = auth.uid()
        )
    );
-- Inserts/updates/deletes go through service role only (backend pipeline)

-- =============================================================================
-- audio_cache — content-addressable TTS cache (global, backend-only)
-- =============================================================================
create table if not exists public.audio_cache (
    content_hash      text primary key,        -- sha256(text|voice|language)
    voice             text not null,
    language          text not null,
    storage_path      text not null,
    duration_sec      numeric,
    size_bytes        bigint,
    hit_count         int not null default 0,
    created_at        timestamptz not null default now(),
    last_accessed_at  timestamptz not null default now()
);
-- No RLS: backend (service_role) reads/writes only.

-- =============================================================================
-- translation_cache — content-addressable translation cache (global)
-- =============================================================================
create table if not exists public.translation_cache (
    content_hash       text primary key,
    source_language    text,
    target_language    text not null,
    translated_text    text not null,
    hit_count          int not null default 0,
    created_at         timestamptz not null default now()
);
-- No RLS: backend-only.

-- =============================================================================
-- conversations — Q/A history + feedback
-- =============================================================================
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

-- =============================================================================
-- user_usage_daily — per-user counters + cost attribution
-- =============================================================================
create table if not exists public.user_usage_daily (
    user_id             uuid not null,
    date                date not null,
    documents_uploaded  int not null default 0,
    pages_processed     int not null default 0,
    tts_chars           int not null default 0,
    rag_queries         int not null default 0,
    cost_usd_estimate   numeric(10,4) not null default 0,
    primary key (user_id, date)
);

alter table public.user_usage_daily enable row level security;

create policy "users read own usage"
    on public.user_usage_daily for select
    using (auth.uid() = user_id);
-- Writes go through service_role only.

-- =============================================================================
-- prompts — versioned prompt registry; exactly one is_active per id (A2 §9)
-- =============================================================================
create table if not exists public.prompts (
    id           text not null,                 -- e.g., 'rag.system'
    version      int not null,
    content      text not null,
    description  text,
    is_active    boolean not null default false,
    created_at   timestamptz not null default now(),
    primary key (id, version)
);
create unique index if not exists prompts_one_active_per_id
    on public.prompts (id) where is_active = true;
-- No user-facing RLS: backend-only writes; reads fetched by backend per-request.

-- =============================================================================
-- audit_log — security-relevant events (A2 §18)
-- 30-day retention via pg_cron (see 0002_pg_cron_jobs.sql)
-- =============================================================================
create table if not exists public.audit_log (
    id             bigserial primary key,
    user_id        uuid,
    action         text not null,                -- e.g., 'document.upload', 'rag.ask'
    resource_type  text,
    resource_id    text,
    metadata       jsonb,                        -- redacted; never raw user content
    ip_hash        text,                         -- sha256(ip || daily_salt)
    created_at     timestamptz not null default now()
);
create index if not exists idx_audit_user_time   on public.audit_log(user_id, created_at desc);
create index if not exists idx_audit_action_time on public.audit_log(action, created_at desc);

alter table public.audit_log enable row level security;

create policy "users read own audit rows"
    on public.audit_log for select
    using (auth.uid() = user_id);
-- Inserts only via service_role.

-- =============================================================================
-- idempotency_keys — replay-safe POST endpoints (A2 §11)
-- 24h TTL via pg_cron
-- =============================================================================
create table if not exists public.idempotency_keys (
    key           text primary key,
    user_id       uuid not null,
    endpoint      text not null,
    request_hash  text not null,
    response      jsonb,
    status_code   int,
    created_at    timestamptz not null default now()
);
create index if not exists idx_idem_user      on public.idempotency_keys(user_id);
create index if not exists idx_idem_created   on public.idempotency_keys(created_at);

alter table public.idempotency_keys enable row level security;

create policy "users manage own idempotency keys"
    on public.idempotency_keys for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- =============================================================================
-- Storage buckets + RLS on storage.objects
-- Path convention: <user_id>/<filename>  → policies enforce ownership
-- =============================================================================
insert into storage.buckets (id, name, public)
values
    ('documents',   'documents',   false),
    ('chunks',      'chunks',      false),
    ('audio-cache', 'audio-cache', false)
on conflict (id) do nothing;

-- documents bucket: per-user folder
create policy "documents bucket — user inserts own folder"
    on storage.objects for insert
    with check (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "documents bucket — user reads own folder"
    on storage.objects for select
    using (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

create policy "documents bucket — user deletes own folder"
    on storage.objects for delete
    using (
        bucket_id = 'documents'
        and auth.uid()::text = (storage.foldername(name))[1]
    );

-- chunks bucket + audio-cache: backend-only (service_role bypasses RLS).
-- No public policies = no end-user access.
