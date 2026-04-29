"""
audio_cache table + Storage helpers (build plan §4, Day 15).

  Cache key:  sha256(text|voice_id)
  Storage:    bucket=audio-cache, path=<hash>.<ext>
              (mp3 for edge-tts, wav for Piper)

The cache is global (no user RLS — backend-only access via service role)
because TTS is content-addressable and the same text in the same voice
yields identical audio across users. Big speedup for repeated passages
(textbook excerpts, scripture lines, news quotes).

Privacy: see docs/SECURITY.md — same shape as translation_cache.
"""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client

from app.services import storage

logger = logging.getLogger(__name__)


def _ext_for_mime(mime: str) -> str:
    if mime == "audio/mpeg":
        return "mp3"
    if mime == "audio/wav":
        return "wav"
    return "bin"


def lookup(db: Client, content_hash: str) -> dict[str, Any] | None:
    """Return the cached row or None. Caller decides whether to download."""
    res = (
        db.table("audio_cache")
        .select("content_hash, voice, language, storage_path, size_bytes")
        .eq("content_hash", content_hash)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def store(
    db: Client,
    *,
    content_hash: str,
    voice_id: str,
    language: str,
    audio_bytes: bytes,
    mime_type: str,
) -> str:
    """
    Upload audio to the audio-cache bucket and insert an audio_cache row.
    Returns the storage_path. Race-tolerant — concurrent identical
    syntheses converge on the same row.
    """
    storage_path = f"{content_hash}.{_ext_for_mime(mime_type)}"

    storage.upload(
        db,
        bucket=storage.BUCKET_AUDIO,
        path=storage_path,
        content=audio_bytes,
        content_type=mime_type,
        upsert=True,
    )

    try:
        db.table("audio_cache").insert(
            {
                "content_hash": content_hash,
                "voice": voice_id,
                "language": language,
                "storage_path": storage_path,
                "size_bytes": len(audio_bytes),
            }
        ).execute()
    except Exception:  # noqa: BLE001 — race tolerated
        logger.debug("audio_cache insert raced for hash=%s", content_hash[:12])

    return storage_path


def download(db: Client, storage_path: str) -> bytes:
    return storage.download(db, storage.BUCKET_AUDIO, storage_path)
