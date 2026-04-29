"""POST /tts — synthesize → cache → signed URL. GET /voices — voice catalog."""

# NOTE: do NOT add `from __future__ import annotations` here.
# FastAPI introspects request-body / response models via pydantic's
# TypeAdapter, which can't resolve PEP 563 stringified forward refs
# in the function signature.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.limiter import limiter
from app.core.security import AuthenticatedUser, current_user
from app.db.supabase import admin_client
from app.models.schemas import TTSRequest, TTSResponse, VoiceOption
from app.services import audio_cache, quotas, storage
from app.services.audit import write_audit
from app.services.tts import TTSError, content_hash, synthesize
from app.services.voices import VOICES

router = APIRouter(tags=["tts"])

SIGNED_URL_TTL_SECONDS = 3600


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _mime_for_path(path: str) -> str:
    if path.endswith(".mp3"):
        return "audio/mpeg"
    if path.endswith(".wav"):
        return "audio/wav"
    return "application/octet-stream"


@router.get("/voices", response_model=list[VoiceOption])
@limiter.limit("60/minute")
async def list_voices(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> list[VoiceOption]:
    """Voice catalog — used by the frontend's voice picker."""
    return [
        VoiceOption(
            voice_id=v.voice_id,
            language=v.language,
            label=v.label,
            gender=v.gender,
        )
        for v in VOICES.values()
    ]


@router.post("/tts", response_model=TTSResponse)
@limiter.limit("20/minute")
async def tts_endpoint(
    request: Request,
    body: TTSRequest,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> TTSResponse:
    """
    Synthesize `text` with `voice_id`. Returns a short-lived signed URL.

    Day 18: 20/min/IP slowapi limit + per-user daily tts_chars cap
    (RATE_LIMIT_DAILY_TTS_CHARS, default 100k chars). Cache hits do NOT
    count against the user's daily char budget — they didn't pay for synth.
    """
    voice = VOICES.get(body.voice_id)
    if voice is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"unknown voice_id: {body.voice_id!r}"
        )

    # Per-user user_client just for quota read; cache lives in admin scope.
    db_user = None  # lazy-init only when needed
    db = admin_client()
    h = content_hash(body.text, body.voice_id)

    # Cache lookup — free for the user, no quota debit.
    cached = audio_cache.lookup(db, h)
    if cached is not None:
        url = storage.signed_url(
            db,
            storage.BUCKET_AUDIO,
            cached["storage_path"],
            ttl_seconds=SIGNED_URL_TTL_SECONDS,
        )
        write_audit(
            action="tts.synthesize",
            user_id=user.user_id,
            ip=_client_ip(request),
            metadata={"voice": body.voice_id, "chars": len(body.text), "cached": True},
        )
        return TTSResponse(
            audio_url=url,
            mime_type=_mime_for_path(cached["storage_path"]),
            voice_id=body.voice_id,
            language=voice.language,
            cached=True,
            size_bytes=cached.get("size_bytes"),
            fallback_used=False,
        )

    # Cache miss → quota check before paying for synthesis.
    from app.db.supabase import user_client

    db_user = user_client(user.access_token)
    quotas.assert_under_cap(
        db_user,
        user_id=user.user_id,
        counter="tts_chars",
        delta=len(body.text),
    )

    try:
        result = await synthesize(body.text, body.voice_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except TTSError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"TTS unavailable: {exc}"
        ) from exc

    storage_path = audio_cache.store(
        db,
        content_hash=h,
        voice_id=body.voice_id,
        language=voice.language,
        audio_bytes=result.audio,
        mime_type=result.mime_type,
    )

    url = storage.signed_url(
        db,
        storage.BUCKET_AUDIO,
        storage_path,
        ttl_seconds=SIGNED_URL_TTL_SECONDS,
    )

    quotas.bump(
        db_user,
        user_id=user.user_id,
        counter="tts_chars",
        delta=len(body.text),
    )

    write_audit(
        action="tts.synthesize",
        user_id=user.user_id,
        ip=_client_ip(request),
        metadata={
            "voice": body.voice_id,
            "chars": len(body.text),
            "cached": False,
            "fallback": result.fallback_used,
        },
    )

    return TTSResponse(
        audio_url=url,
        mime_type=result.mime_type,
        voice_id=body.voice_id,
        language=voice.language,
        cached=False,
        size_bytes=len(result.audio),
        fallback_used=result.fallback_used,
    )
