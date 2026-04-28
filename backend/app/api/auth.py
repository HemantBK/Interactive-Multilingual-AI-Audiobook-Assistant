"""Auth-related endpoints: /me, /login, /logout (audit hooks)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.security import AuthenticatedUser, current_user
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    # HF Spaces / Cloudflare set X-Forwarded-For; trust the leftmost entry.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/me")
async def me(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> dict[str, str | None]:
    """Return the authenticated user. 401 if token missing or invalid."""
    return {"user_id": user.user_id, "email": user.email}


@router.post("/login")
async def login_event(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> dict[str, bool]:
    """
    Frontend calls this once per fresh sign-in (after Supabase magic-link or
    OAuth completes). Writes an `auth.login` row to audit_log.
    """
    write_audit(
        action="auth.login",
        user_id=user.user_id,
        ip=_client_ip(request),
        metadata={"has_email": user.email is not None},
    )
    return {"ok": True}


@router.post("/logout")
async def logout_event(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> dict[str, bool]:
    """
    Frontend calls this before invoking Supabase `signOut`. Writes an
    `auth.logout` row. Session invalidation itself happens client-side via
    Supabase; this endpoint exists for the audit trail only.
    """
    write_audit(
        action="auth.logout",
        user_id=user.user_id,
        ip=_client_ip(request),
    )
    return {"ok": True}
