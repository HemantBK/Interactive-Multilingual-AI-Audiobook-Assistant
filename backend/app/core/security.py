"""
FastAPI auth dependencies.

Verifies Supabase JWT from the `Authorization: Bearer <token>` header by asking
Supabase itself (`auth.get_user(token)`). We do not cache verifications — a
revoked session must stop working immediately. Supabase's endpoint is fast.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.db.supabase import admin_client

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    user_id: str
    email: str | None = None
    access_token: str


def _verify(token: str) -> AuthenticatedUser | None:
    try:
        resp = admin_client().auth.get_user(token)
    except Exception:
        return None
    user = resp.user
    if user is None:
        return None
    return AuthenticatedUser(
        user_id=str(user.id),
        email=getattr(user, "email", None),
        access_token=token,
    )


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    user = _verify(creds.credentials)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return user


async def optional_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    return _verify(creds.credentials)
