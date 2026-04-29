"""
Idempotency-key check + store for write endpoints (build plan §11).

Strategy:
  - Caller provides `Idempotency-Key: <uuid>`. Required on mutating requests.
  - Endpoint computes `request_hash` from the request payload (handler-specific).
  - On replay with same hash → return the cached response.
  - On replay with different hash → 409 (key reused with different payload).
  - 24h TTL handled by pg_cron (`aria_idempotency_cleanup` in 0002_pg_cron_jobs.sql).

Storage uses the user's RLS-scoped client so a malicious user cannot read
or overwrite another user's idempotency rows.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from supabase import Client


class IdempotencyConflictError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key reused with a different request payload",
        )


def lookup(
    *, client: Client, key: str, user_id: str, endpoint: str
) -> dict[str, Any] | None:
    res = (
        client.table("idempotency_keys")
        .select("request_hash, response, status_code")
        .eq("key", key)
        .eq("user_id", user_id)
        .eq("endpoint", endpoint)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def store(
    *,
    client: Client,
    key: str,
    user_id: str,
    endpoint: str,
    request_hash: str,
    response: dict[str, Any],
    status_code: int = 200,
) -> None:
    client.table("idempotency_keys").insert(
        {
            "key": key,
            "user_id": user_id,
            "endpoint": endpoint,
            "request_hash": request_hash,
            "response": response,
            "status_code": status_code,
        }
    ).execute()
