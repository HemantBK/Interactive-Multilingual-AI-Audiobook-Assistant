-- =============================================================================
-- ARIA — atomic per-user daily quota counter (build plan §6, §11, Day 18)
--
-- Increments one of the user_usage_daily counters atomically and returns
-- the post-increment value. The caller compares against the configured
-- daily cap and rejects (HTTP 429) when exceeded.
--
-- security definer because authenticated users have RLS-read-only access
-- to user_usage_daily. The function bypasses RLS as the function owner.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Up
-- -----------------------------------------------------------------------------
create or replace function public.bump_user_usage(
    p_user_id uuid,
    p_counter text,
    p_delta   int
)
returns int
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    v_new   int;
    v_today date := (now() at time zone 'utc')::date;
begin
    -- Ensure a row exists for today (no-op if it already does).
    insert into public.user_usage_daily (user_id, date)
    values (p_user_id, v_today)
    on conflict (user_id, date) do nothing;

    case p_counter
    when 'documents_uploaded' then
        update public.user_usage_daily
           set documents_uploaded = documents_uploaded + p_delta
         where user_id = p_user_id and date = v_today
         returning documents_uploaded into v_new;
    when 'pages_processed' then
        update public.user_usage_daily
           set pages_processed = pages_processed + p_delta
         where user_id = p_user_id and date = v_today
         returning pages_processed into v_new;
    when 'tts_chars' then
        update public.user_usage_daily
           set tts_chars = tts_chars + p_delta
         where user_id = p_user_id and date = v_today
         returning tts_chars into v_new;
    when 'rag_queries' then
        update public.user_usage_daily
           set rag_queries = rag_queries + p_delta
         where user_id = p_user_id and date = v_today
         returning rag_queries into v_new;
    else
        raise exception 'unknown counter: %', p_counter;
    end case;

    return v_new;
end;
$$;

grant execute on function public.bump_user_usage(uuid, text, int) to authenticated;

-- -----------------------------------------------------------------------------
-- Down
-- -----------------------------------------------------------------------------
-- drop function if exists public.bump_user_usage(uuid, text, int);
