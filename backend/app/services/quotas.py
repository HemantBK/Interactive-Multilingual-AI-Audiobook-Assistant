"""
Per-user daily usage quotas (build plan §6, §11, Day 18).

  Counters live in user_usage_daily.{documents_uploaded, pages_processed,
                                     tts_chars, rag_queries}
  Bumping is atomic via the bump_user_usage RPC (0004 migration).
  Cap source-of-truth: settings.RATE_LIMIT_DAILY_*

Pattern at every guarded endpoint:

    quotas.assert_under_cap(db, user_id, counter, delta=1)
    # ... do the work ...
    quotas.bump(db, user_id, counter, delta=1)

We split read-check from increment so that a request that fails *during*
processing (e.g. Groq returns 503) doesn't burn the user's quota. If
processing succeeds, we bump. If we want to charge for failed calls in
v2, swap to a single bump+rollback pattern.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Final, Literal

from fastapi import HTTPException, status
from supabase import Client

from app.core.config import settings

logger = logging.getLogger(__name__)

Counter = Literal[
    "documents_uploaded",
    "pages_processed",
    "tts_chars",
    "rag_queries",
]

CAP_BY_COUNTER: Final[dict[Counter, int]] = {
    "documents_uploaded": settings.rate_limit_daily_uploads,
    "rag_queries": settings.rate_limit_daily_queries,
    "tts_chars": settings.rate_limit_daily_tts_chars,
    # pages_processed has no cap by default (it's an observation counter)
    "pages_processed": 10**9,
}


class QuotaExceededError(HTTPException):
    def __init__(self, counter: str, current: int, cap: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily {counter} quota exceeded ({current}/{cap}).",
        )


def _today_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).date().isoformat()


def _read_current(db: Client, user_id: str, counter: Counter) -> int:
    res = (
        db.table("user_usage_daily")
        .select(counter)
        .eq("user_id", user_id)
        .eq("date", _today_iso())
        .limit(1)
        .execute()
    )
    if not res.data:
        return 0
    return int(res.data[0].get(counter) or 0)


def assert_under_cap(
    db: Client,
    *,
    user_id: str,
    counter: Counter,
    delta: int = 1,
    cap: int | None = None,
) -> None:
    """
    Raise QuotaExceededError if `current + delta > cap`. cap=None reads
    from CAP_BY_COUNTER. Use a custom cap to override (e.g. tts_chars
    where delta is len(text)).
    """
    effective_cap = CAP_BY_COUNTER[counter] if cap is None else cap
    current = _read_current(db, user_id, counter)
    if current + delta > effective_cap:
        raise QuotaExceededError(counter, current, effective_cap)


def bump(
    db: Client,
    *,
    user_id: str,
    counter: Counter,
    delta: int = 1,
) -> int:
    """
    Atomic bump via bump_user_usage RPC. Returns the post-increment value.
    Best-effort: failures are logged but not raised — bookkeeping must
    never break the user-facing path.
    """
    try:
        res = db.rpc(
            "bump_user_usage",
            {
                "p_user_id": user_id,
                "p_counter": counter,
                "p_delta": delta,
            },
        ).execute()
        return int(res.data) if res.data is not None else 0
    except Exception:  # noqa: BLE001
        logger.exception(
            "bump_user_usage failed (user=%s counter=%s delta=%d)",
            user_id,
            counter,
            delta,
        )
        return 0
