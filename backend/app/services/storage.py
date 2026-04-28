"""
Thin Supabase Storage helpers — wraps supabase-py to keep call sites tidy
and centralise the bucket-name constants.
"""

from __future__ import annotations

from typing import Final

from supabase import Client

BUCKET_DOCUMENTS: Final = "documents"
BUCKET_CHUNKS: Final = "chunks"
BUCKET_AUDIO: Final = "audio-cache"


def download(client: Client, bucket: str, path: str) -> bytes:
    """Returns raw bytes. Raises on 404 / 403."""
    return client.storage.from_(bucket).download(path)


def upload(
    client: Client,
    bucket: str,
    path: str,
    content: bytes,
    *,
    content_type: str = "application/octet-stream",
    upsert: bool = False,
) -> None:
    file_options: dict[str, str] = {"content-type": content_type}
    if upsert:
        file_options["upsert"] = "true"
    client.storage.from_(bucket).upload(
        path=path, file=content, file_options=file_options
    )


def signed_url(
    client: Client,
    bucket: str,
    path: str,
    *,
    ttl_seconds: int = 3600,
) -> str:
    """
    Issue a short-lived signed URL for a private object. Used for audio
    playback on the frontend (no backend in the audio data path).
    supabase-py 2.x returns {'signedURL': str}; we tolerate either casing.
    """
    res = client.storage.from_(bucket).create_signed_url(path, ttl_seconds)
    if isinstance(res, dict):
        url = res.get("signedURL") or res.get("signed_url")
        if url:
            return url
    raise RuntimeError(f"create_signed_url returned unexpected shape: {res!r}")
