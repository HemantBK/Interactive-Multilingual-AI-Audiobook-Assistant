"""
Conversations table writer (Day 9).

Persists Q/A history with cited chunks, token usage, latency, and model
version. Used by:
  - feedback loops (Day 31): thumbs_up/down via PATCH /conversations/:id
  - prompt iteration (Day 33): mining low-rated answers for the eval set
  - cost attribution (Day 21): aggregating tokens_in/out per user/day

RLS enforces user_id == auth.uid() on insert. Best-effort: failures are
logged, not raised, so a sick conversations table doesn't break /rag/ask.
"""

from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger(__name__)


def persist_conversation(
    db: Client,
    *,
    user_id: str,
    document_id: str,
    question: str,
    answer: str,
    cited_chunk_ids: list[int],
    latency_ms: int,
    tokens_in: int | None,
    tokens_out: int | None,
    model: str,
) -> None:
    try:
        db.table("conversations").insert(
            {
                "document_id": document_id,
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "cited_chunks": cited_chunk_ids,
                "latency_ms": latency_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "model": model,
            }
        ).execute()
    except Exception:  # noqa: BLE001 — best-effort write
        logger.exception(
            "conversations insert failed (doc=%s, user=%s)", document_id, user_id
        )
