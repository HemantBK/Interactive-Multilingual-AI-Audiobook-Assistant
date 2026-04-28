"""
pgvector retrieval via the `search_chunks` RPC.

The query vector is sent as a `[v1,v2,...]` text literal because supabase-py
RPC params go over JSON — Postgres casts to halfvec(1024) inside the function.

RLS stays in force: `search_chunks` uses `security invoker`, so the caller's
JWT is what RLS checks against `document_chunks`.
"""

from __future__ import annotations

from typing import Any

from supabase import Client


def _format_embedding(vec: list[float]) -> str:
    """Render a float vector as a pgvector text literal."""
    return "[" + ",".join(f"{v:.7f}" for v in vec) + "]"


def retrieve_top_k(
    db: Client,
    document_id: str,
    query_embedding: list[float],
    *,
    k: int = 20,
) -> list[dict[str, Any]]:
    res = db.rpc(
        "search_chunks",
        {
            "p_document_id": document_id,
            "p_query_embedding": _format_embedding(query_embedding),
            "p_match_count": k,
        },
    ).execute()
    return list(res.data or [])
