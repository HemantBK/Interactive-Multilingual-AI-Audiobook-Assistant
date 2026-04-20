"""Auth-related endpoints (minimal for v1)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import AuthenticatedUser, current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> dict[str, str | None]:
    """Returns the authenticated user. 401 if the token is missing or invalid."""
    return {"user_id": user.user_id, "email": user.email}
