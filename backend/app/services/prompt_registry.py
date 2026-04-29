"""
public.prompts table helpers (build plan §9).

Day 9 registers the baseline rag.system prompt at backend startup,
idempotently. Existing rows are not overwritten; the first ever insert
for a given prompt_id is marked is_active=true so retrieval has a
deterministic default.

Day 33 wires the prompt iteration A/B runner — new versions land here
with is_active=false; eval/runners/prompt_compare.py promotes a winner
by flipping is_active.
"""

from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger(__name__)


def ensure_prompt_registered(
    db: Client,
    *,
    prompt_id: str,
    version: int,
    content: str,
    description: str | None = None,
) -> bool:
    """Idempotent. Returns True on insert, False if (id, version) exists."""
    existing = (
        db.table("prompts")
        .select("version, is_active")
        .eq("id", prompt_id)
        .execute()
    )
    rows = existing.data or []
    if any(r["version"] == version for r in rows):
        return False

    is_first = len(rows) == 0
    db.table("prompts").insert(
        {
            "id": prompt_id,
            "version": version,
            "content": content,
            "description": description,
            "is_active": is_first,
        }
    ).execute()
    logger.info(
        "registered prompt %s v%d (active=%s)", prompt_id, version, is_first
    )
    return True


def load_active_prompt_content(db: Client, prompt_id: str) -> str | None:
    """Return the content of the active prompt for `prompt_id`, or None."""
    res = (
        db.table("prompts")
        .select("content")
        .eq("id", prompt_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0]["content"]
