"""
Translation service — Groq Llama 3.3 70B + content-addressable cache.

Cache key:  sha256(text|target_language)
Cache hit:  0 ms LLM time
Cache miss: ~1 s LLM call, then INSERT (best-effort, races between workers
            are silently dropped because the row already exists).

The translation_cache table has no user-facing RLS policy — it's a global
cache accessed by the backend's service-role key only. A privacy note in
docs/SECURITY.md (Day 25) covers what this implies for user-uploaded text.

Supported targets: 14 languages per build plan §1. The set is closed —
unknown codes return ValueError.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Final

from supabase import Client

from app.services.groq_client import groq_stream_chat

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS: Final = 8000

# 14 target languages (build plan §1).
SUPPORTED_LANGUAGES: Final[dict[str, str]] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "pt": "Portuguese",
    "it": "Italian",
    "ru": "Russian",
}


def content_hash(text: str, target_language: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    h.update(b"|")
    h.update(target_language.encode("ascii"))
    return h.hexdigest()


def _cache_lookup(db: Client, key: str) -> str | None:
    res = (
        db.table("translation_cache")
        .select("translated_text")
        .eq("content_hash", key)
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]["translated_text"]
    return None


def _cache_store(
    db: Client,
    *,
    key: str,
    source_language: str | None,
    target_language: str,
    translated_text: str,
) -> None:
    try:
        db.table("translation_cache").insert(
            {
                "content_hash": key,
                "source_language": source_language,
                "target_language": target_language,
                "translated_text": translated_text,
            }
        ).execute()
    except Exception:  # noqa: BLE001
        # Race with another worker — the row already exists. Caller has the
        # translation in hand from the LLM call; the cache will serve the
        # next reader.
        logger.debug("translation_cache insert raced for key=%s", key[:12])


async def _call_groq(
    text: str, target_language: str, source_language: str | None
) -> str:
    target_name = SUPPORTED_LANGUAGES[target_language]
    source_hint = ""
    if source_language and source_language in SUPPORTED_LANGUAGES:
        source_hint = (
            f"The source text is in {SUPPORTED_LANGUAGES[source_language]}. "
        )

    system = (
        f"You are a professional translator. Translate the user's text into "
        f"{target_name}. {source_hint}"
        "Return ONLY the translation as plain text. No commentary, no quotes, "
        "no source-language echo. Preserve paragraph breaks. If the text is "
        "already in the target language, return it unchanged."
    )

    parts: list[str] = []
    async for tok in groq_stream_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    ):
        parts.append(tok)

    return "".join(parts).strip()


async def translate(
    db: Client,
    text: str,
    target_language: str,
    source_language: str | None = None,
) -> tuple[str, bool]:
    """
    Returns (translated_text, cached). Raises:
      ValueError on bad input.
      GroqUnavailableError (from groq_client) on LLM failure.
    """
    if not text or not text.strip():
        raise ValueError("text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text exceeds {MAX_TEXT_CHARS} chars")
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported target_language: {target_language}")
    if (
        source_language is not None
        and source_language not in SUPPORTED_LANGUAGES
    ):
        raise ValueError(f"unsupported source_language: {source_language}")

    key = content_hash(text, target_language)
    cached = _cache_lookup(db, key)
    if cached is not None:
        return cached, True

    translated = await _call_groq(text, target_language, source_language)
    _cache_store(
        db,
        key=key,
        source_language=source_language,
        target_language=target_language,
        translated_text=translated,
    )
    return translated, False
