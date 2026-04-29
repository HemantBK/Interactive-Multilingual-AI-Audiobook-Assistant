-- =============================================================================
-- ARIA — pg_cron jobs (build plan, Day 2)
--
-- PREREQUISITE: enable pg_cron in the Supabase dashboard
--   Database → Extensions → pg_cron → toggle on
-- (or run `create extension pg_cron;` from a service-role SQL session)
--
-- All schedules are UTC. India offset is +05:30, so 21:30 UTC = 03:00 IST.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Up
-- -----------------------------------------------------------------------------
create extension if not exists pg_cron;

-- 14-day document cleanup (build plan §1: retention ≤ 14 days unless user opts in)
-- Skipped for documents that have a row in documents_keepalive.
select cron.schedule(
    'aria_doc_cleanup_14d',
    '30 21 * * *',
    $cron$
        delete from public.documents
        where created_at < now() - interval '14 days'
          and not exists (
              select 1 from public.documents_keepalive k
              where k.document_id = documents.id
          );
    $cron$
);

-- Idempotency keys: 24h TTL (build plan §4)
select cron.schedule(
    'aria_idempotency_cleanup',
    '17 * * * *',
    $cron$
        delete from public.idempotency_keys
        where created_at < now() - interval '24 hours';
    $cron$
);

-- audit_log retention: 30 days
select cron.schedule(
    'aria_audit_log_retention',
    '45 21 * * *',
    $cron$
        delete from public.audit_log
        where created_at < now() - interval '30 days';
    $cron$
);

-- conversations retention: 14 days (matches document retention)
-- Skipped if the parent document has a keepalive row.
select cron.schedule(
    'aria_conversations_retention',
    '35 21 * * *',
    $cron$
        delete from public.conversations c
        where c.created_at < now() - interval '14 days'
          and not exists (
              select 1 from public.documents_keepalive k
              where k.document_id = c.document_id
          );
    $cron$
);

-- =============================================================================
-- Down (run by hand if rolling back)
-- =============================================================================
-- select cron.unschedule('aria_doc_cleanup_14d');
-- select cron.unschedule('aria_idempotency_cleanup');
-- select cron.unschedule('aria_audit_log_retention');
-- select cron.unschedule('aria_conversations_retention');
