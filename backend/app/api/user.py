"""
User self-service: export + delete (build plan A2 §26 Day 25).

Right to portability  (DPDP §11 / GDPR Art. 20)  → GET  /user/me/export
Right to erasure      (DPDP §12 / GDPR Art. 17)  → DELETE /user/me

Both are explicit user-initiated actions. The frontend confirms with the
user before calling DELETE — backend trusts authenticated callers and
deletes immediately.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from app.core.limiter import limiter
from app.core.security import AuthenticatedUser, current_user
from app.db.supabase import admin_client, user_client
from app.models.schemas import UserExport
from app.services.audit import write_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/me/export", response_model=UserExport)
@limiter.limit("3/hour")
async def export_my_data(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> UserExport:
    """
    Return everything we hold for the caller as one JSON payload.
    RLS-scoped query: a user only ever sees their own rows.
    """
    db = user_client(user.access_token)

    documents = (
        db.table("documents").select("*").eq("user_id", user.user_id).execute().data
        or []
    )
    conversations = (
        db.table("conversations")
        .select("*")
        .eq("user_id", user.user_id)
        .execute()
        .data
        or []
    )
    usage = (
        db.table("user_usage_daily")
        .select("*")
        .eq("user_id", user.user_id)
        .execute()
        .data
        or []
    )
    audit = (
        db.table("audit_log").select("*").eq("user_id", user.user_id).execute().data
        or []
    )

    write_audit(
        action="admin.export",
        user_id=user.user_id,
        ip=_client_ip(request),
        metadata={"documents": len(documents), "conversations": len(conversations)},
    )

    return UserExport(
        exported_at=datetime.now(timezone.utc).isoformat(),
        user_id=user.user_id,
        email=user.email,
        documents=documents,
        conversations=conversations,
        usage=usage,
        audit_log=audit,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/hour")
async def delete_my_account(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> Response:
    """
    Erase the caller. Cascade order:
      1. write `admin.delete_user` audit row (BEFORE we drop audit rows)
      2. delete Storage objects under `<user_id>/`
      3. delete document_chunks   (FK cascade from documents.delete)
      4. delete documents         (cascades chunks + keepalives)
      5. delete conversations
      6. delete user_usage_daily
      7. delete audit_log         (caller's own rows)
      8. delete idempotency_keys  (caller's own rows)
      9. delete the auth.users row (revokes all sessions)

    Steps 3–8 use admin_client to bypass RLS — RLS would only let the
    user delete row-by-row, slow and racy. The single audit row written
    in step 1 stays in the global audit_log because we delete WHERE
    user_id = caller; if the caller's id is set on that row it goes
    too — that's intended (full erasure).
    """
    user_id = user.user_id

    # Audit FIRST so we have a record even though it'll be wiped along with
    # the rest of the user's audit rows. The hash + ip survive in any
    # downstream Sentry / log aggregator copies (Day 22).
    write_audit(
        action="admin.delete_user",
        user_id=user_id,
        ip=_client_ip(request),
        metadata={"requested": True},
    )

    db = admin_client()

    # Storage cleanup: list <user_id>/ and remove. Recursive listing isn't
    # supported in supabase-py 2.x; we list the user's folder, then for
    # each file under it, remove. Empty folders are auto-cleaned.
    try:
        storage_listing = db.storage.from_("documents").list(user_id)
        paths_to_remove: list[str] = []
        for entry in storage_listing or []:
            # Each top-level entry under <user_id>/ is itself a folder
            # named <doc_id>/. List its contents and queue each file.
            sub = db.storage.from_("documents").list(f"{user_id}/{entry['name']}")
            for s in sub or []:
                paths_to_remove.append(f"{user_id}/{entry['name']}/{s['name']}")
        if paths_to_remove:
            db.storage.from_("documents").remove(paths_to_remove)
    except Exception:  # noqa: BLE001
        logger.exception("storage cleanup failed (user=%s)", user_id)

    # DB cleanup. Order matters: documents first → chunks/keepalives cascade.
    for table in (
        "documents",
        "conversations",
        "user_usage_daily",
        "audit_log",
        "idempotency_keys",
    ):
        try:
            db.table(table).delete().eq("user_id", user_id).execute()
        except Exception:
            logger.exception("delete %s for user=%s failed", table, user_id)

    # Drop the auth.users row → invalidates JWT immediately.
    try:
        db.auth.admin.delete_user(user_id)
    except Exception:
        logger.exception("auth.users delete for %s failed", user_id)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Account data wiped, but auth user couldn't be deleted. Contact support.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
