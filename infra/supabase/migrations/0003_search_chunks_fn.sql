-- =============================================================================
-- ARIA — search_chunks RPC (build plan A2 Day 8)
--
-- pgvector cosine similarity over halfvec(1024). Caller passes the query
-- vector as a `[v1,v2,...]` text literal; the function casts to halfvec.
-- RLS stays in force via security invoker — the caller's user_id is checked
-- by the document_chunks policies, so users can only search their own docs.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Up
-- -----------------------------------------------------------------------------
create or replace function public.search_chunks(
    p_document_id     uuid,
    p_query_embedding text,           -- '[v1,v2,...]' textual halfvec
    p_match_count     int default 20
)
returns table (
    id                bigint,
    chunk_index       int,
    text_storage_path text,
    page_number       int,
    char_start        int,
    char_end          int,
    bbox              jsonb,
    similarity        real
)
language sql
stable
security invoker
as $$
    select
        c.id,
        c.chunk_index,
        c.text_storage_path,
        c.page_number,
        c.char_start,
        c.char_end,
        c.bbox,
        (1 - (c.embedding <=> p_query_embedding::halfvec(1024)))::real as similarity
    from public.document_chunks c
    where c.document_id = p_document_id
    order by c.embedding <=> p_query_embedding::halfvec(1024)
    limit greatest(1, least(p_match_count, 100));
$$;

grant execute on function public.search_chunks(uuid, text, int) to authenticated;

-- -----------------------------------------------------------------------------
-- Down
-- -----------------------------------------------------------------------------
-- drop function if exists public.search_chunks(uuid, text, int);
