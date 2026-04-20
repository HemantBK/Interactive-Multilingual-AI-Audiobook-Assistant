# Supabase setup

## 1. Create project
1. Sign in at https://supabase.com
2. New project → name `aria`, region **Mumbai (ap-south-1)**, choose a strong DB password and save it somewhere safe
3. Wait 2–3 minutes for provisioning

## 2. Apply initial migration
Open **SQL Editor** in Supabase dashboard → paste the contents of `migrations/0001_initial_schema.sql` → **Run**.

Verify: `SELECT tablename FROM pg_tables WHERE schemaname='public';` should list `documents`, `document_chunks`, `audio_cache`, `translation_cache`, `conversations`, `user_usage_daily`.

## 3. Create Storage buckets
In **Storage** section:
- `documents` — private (user uploads)
- `audio-cache` — private (TTS cache)

## 4. Configure Auth
**Authentication → Providers**:
- Email: enable magic link
- Google: enable (needs OAuth credentials — later)

**Authentication → URL Configuration**:
- Site URL: your Cloudflare Pages URL once deployed
- Redirect URLs: same + `http://localhost:5173` for dev

## 5. Grab keys
**Project Settings → API**:
- `anon public` key → frontend `.env` as `VITE_SUPABASE_ANON_KEY`
- `service_role secret` key → backend `.env` as `SUPABASE_SERVICE_KEY` (never expose to browser)
- Project URL → both as `SUPABASE_URL` / `VITE_SUPABASE_URL`
