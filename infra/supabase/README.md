# Supabase setup

## 1. Create project
1. Sign in at https://supabase.com
2. **New project** → name `aria`, region **Mumbai (ap-south-1)**, choose a strong DB password and save it somewhere safe
3. Wait 2–3 minutes for provisioning

## 2. Enable required extensions
**Database → Extensions** — toggle on:
- `pg_cron` (for scheduled cleanup jobs)
- `uuid-ossp` and `vector` are enabled by `0001_initial_schema.sql`

## 3. Apply initial migration
**SQL Editor** → paste `migrations/0001_initial_schema.sql` → **Run**.

Verify:
```sql
select tablename from pg_tables where schemaname = 'public' order by tablename;
```
Expected (10 tables):
```
audio_cache
audit_log
conversations
document_chunks
documents
documents_keepalive
idempotency_keys
prompts
translation_cache
user_usage_daily
```

The migration also creates three Storage buckets — **`documents`** (per-user uploads, RLS by folder), **`chunks`** (chunk text, backend-only), **`audio-cache`** (TTS cache, backend-only). Verify in **Storage**.

## 4. Apply pg_cron jobs
**SQL Editor** → paste `migrations/0002_pg_cron_jobs.sql` → **Run**.

Verify:
```sql
select jobname, schedule, active from cron.job;
```
Expected jobs:
- `aria_doc_cleanup_14d` (daily 21:30 UTC)
- `aria_idempotency_cleanup` (hourly :17)
- `aria_audit_log_retention` (daily 21:45 UTC)
- `aria_conversations_retention` (daily 21:35 UTC)

## 5. Configure Auth
**Authentication → Providers**:
- **Email**: enable magic link
- **Google**: enable (needs OAuth credentials — set up in Google Cloud Console)

**Authentication → URL Configuration**:
- Site URL: your Cloudflare Pages URL once deployed
- Redirect URLs: same + `http://localhost:5173` for dev

## 6. Grab keys
**Project Settings → API**:
- `anon public` → frontend `.env` as `VITE_SUPABASE_ANON_KEY`
- `service_role secret` → backend `.env` as `SUPABASE_SERVICE_KEY` (NEVER expose to browser)
- Project URL → both `SUPABASE_URL` and `VITE_SUPABASE_URL`

## Migrations going forward

From `0002` onward, every migration ships with both an `-- Up` and `-- Down` block (build plan A2 §16). CI verifies migrations apply cleanly on a shadow DB before they touch `main`.
