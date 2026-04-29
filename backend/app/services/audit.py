"""
Audit-log service.

Writes security-relevant events (auth.login/logout, document.upload, rag.ask,
etc.) to the `audit_log` table.

Best-effort: failures are logged but do not propagate. Losing an audit row is
preferable to breaking a user-facing request.

Privacy:
  - IPs are hashed with the current UTC date as salt (sha256). Same IP on
    the same day → same hash (allows rate-limit / abuse correlation).
    Across days, the hash is opaque.
  - User content (raw questions, document text) MUST NOT appear in metadata.
    Use stable identifiers (resource_id) and high-level facts only.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from app.db.supabase import admin_client

logger = logging.getLogger(__name__)


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    today = datetime.now(UTC).date().isoformat()
    digest = hashlib.sha256(f"{ip}|{today}".encode()).hexdigest()
    return digest[:32]


def write_audit(
    *,
    action: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Write one audit_log row. Never raises; logs failures."""
    try:
        admin_client().table("audit_log").insert(
            {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": metadata,
                "ip_hash": _hash_ip(ip),
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit_log write failed (action=%s): %s", action, exc)
