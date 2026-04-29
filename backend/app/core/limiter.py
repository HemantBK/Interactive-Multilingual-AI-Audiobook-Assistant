"""
slowapi setup — per-IP rate limits (build plan §6, Day 18).

Why per-IP and not per-user: pre-auth attempts (sign-in storms) and
unauthenticated probes still need throttling. After auth, per-user
daily caps in app.services.quotas take over.

The custom key_func reads X-Forwarded-For so we get the real client IP
behind Cloudflare → HF Spaces, not the proxy address. Falls back to
request.client.host if the header is missing (local dev).

Storage: in-memory (slowapi default). Fine for HF Spaces single-worker;
if we move to multi-worker / multi-replica (v1.5+, Fly.io shared-CPU),
swap to Redis storage via slowapi's `storage_uri='redis://...'`.
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def remote_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Default = configured per-IP-per-min cap. Per-endpoint overrides apply on top.
_default_limit = f"{settings.rate_limit_per_ip_per_min}/minute"

limiter = Limiter(
    key_func=remote_ip,
    default_limits=[_default_limit],
    headers_enabled=True,
)
