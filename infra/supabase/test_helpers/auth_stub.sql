-- =============================================================================
-- Test-fixture only — DO NOT apply to production Supabase.
--
-- Stubs the Supabase platform schemas (auth, storage) for migration dry-run
-- on a vanilla Postgres + pgvector image in CI. Production Supabase
-- provides these via its bootstrap migrations.
-- =============================================================================

-- ---------- roles ----------
-- Supabase pre-creates these. Vanilla Postgres does not, so `grant ... to
-- authenticated` etc. would fail under ON_ERROR_STOP. Create as nologin so
-- they're inert in the shadow DB.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        create role service_role nologin;
    end if;
end $$;

-- ---------- auth ----------
create schema if not exists auth;

create table if not exists auth.users (
    id                  uuid primary key,
    email               text,
    raw_app_meta_data   jsonb,
    raw_user_meta_data  jsonb,
    created_at          timestamptz not null default now()
);

create or replace function auth.uid() returns uuid
language sql stable as $$
    select null::uuid;
$$;

-- ---------- storage ----------
create schema if not exists storage;

create table if not exists storage.buckets (
    id      text primary key,
    name    text not null,
    public  boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists storage.objects (
    bucket_id  text references storage.buckets(id),
    name       text,
    owner      uuid,
    created_at timestamptz not null default now()
);

create or replace function storage.foldername(name text) returns text[]
language sql immutable as $$
    select string_to_array(name, '/');
$$;

-- pgvector + uuid-ossp present in the pgvector/pgvector image already.
-- pg_cron is NOT — the workflow skips 0002_pg_cron_jobs.sql when applying
-- migrations against this stub.
