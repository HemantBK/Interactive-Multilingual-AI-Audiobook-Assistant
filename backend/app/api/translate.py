"""POST /translate — Groq + cached, 14 supported target languages."""

# NOTE: do NOT add `from __future__ import annotations` here.
# FastAPI introspects request-body / response models via pydantic's
# TypeAdapter, which can't resolve PEP 563 stringified forward refs
# in the function signature — would raise PydanticUndefinedAnnotation
# at import time.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.limiter import limiter
from app.core.security import AuthenticatedUser, current_user
from app.db.supabase import admin_client
from app.models.schemas import TranslateRequest, TranslateResponse
from app.services.audit import write_audit
from app.services.groq_client import GroqUnavailableError
from app.services.translate import translate

router = APIRouter(tags=["translate"])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit("30/minute")
async def translate_endpoint(
    request: Request,
    body: TranslateRequest,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> TranslateResponse:
    """
    Translate text into one of 14 supported languages. Cached by
    sha256(text|target_language).

    Day 18: 30/min/IP slowapi limit. No per-user daily cap on translate
    in v1 — usage is bounded by tts_chars and rag_queries, and the
    cache eats most repeated calls anyway.
    """
    db = admin_client()

    try:
        translated, cached = await translate(
            db,
            body.text,
            body.target_language,
            body.source_language,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except GroqUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"LLM unavailable: {exc}"
        ) from exc

    write_audit(
        action="translate",
        user_id=user.user_id,
        ip=_client_ip(request),
        metadata={
            "chars": len(body.text),
            "target": body.target_language,
            "source": body.source_language,
            "cached": cached,
        },
    )

    return TranslateResponse(
        translated_text=translated,
        cached=cached,
        source_language=body.source_language,
        target_language=body.target_language,
    )
