"""
Unified TTS — edge-tts primary, Piper fallback (build plan A2 §3, Day 15).

  synthesize(text, voice_id)
       │
       ▼
   edge-tts (best Indic naturalness, reverse-engineered, no SLA)
       │
       │ (engine error / empty audio)
       ▼
   piper (local CPU, MIT, license-clean — Day 21 wires real voice files)

The HTTP layer (Day 16) wraps this with audio_cache lookup so repeated
requests skip both engines entirely.

Synthesis is async (edge-tts is); but it does NOT stream tokens through
this surface. The HTTP layer reads the bytes-or-cached-Storage-URL and
streams from there.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Final

from app.services.voices import VOICES, VoiceSpec

logger = logging.getLogger(__name__)

# Edge-TTS handles longer input but we cap to keep latency + memory bounded.
# 4000 chars ≈ 2–3 minutes of speech; chunked synthesis (Day 16) handles longer docs.
MAX_TTS_CHARS: Final = 4000


class TTSError(Exception):
    """Raised when every available engine has failed."""


@dataclass(frozen=True)
class SynthesisResult:
    audio: bytes
    mime_type: str         # "audio/mpeg" for edge-tts, "audio/wav" for Piper
    voice: VoiceSpec
    fallback_used: bool


def content_hash(text: str, voice_id: str) -> str:
    """Cache key — same text + same voice ⇒ same audio."""
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    h.update(b"|")
    h.update(voice_id.encode("ascii"))
    return h.hexdigest()


# ----------------------------------------------------------------------------
# Engine implementations
# ----------------------------------------------------------------------------


async def _synthesize_edge_tts(text: str, voice: VoiceSpec) -> bytes:
    """Returns MP3 bytes. Raises on transport / engine error / empty result."""
    # Lazy import — edge-tts pulls a websocket client and we don't want it
    # in the critical path of /health.
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice.engine_voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise TTSError(f"edge-tts produced no audio for voice={voice.voice_id}")
    return bytes(audio)


async def _synthesize_piper(text: str, voice: VoiceSpec) -> bytes:
    """
    Piper local TTS. Day 21 polish wires the real voice ONNX files into
    the Docker image. Until then this raises so the unified synthesizer
    propagates the upstream edge-tts error to the caller.
    """
    raise TTSError("Piper voices not loaded yet (lands Day 21)")


# ----------------------------------------------------------------------------
# Public surface
# ----------------------------------------------------------------------------


async def synthesize(text: str, voice_id: str) -> SynthesisResult:
    """Synthesize via edge-tts; on failure, retry via Piper."""
    if not text or not text.strip():
        raise ValueError("text is empty")
    if len(text) > MAX_TTS_CHARS:
        raise ValueError(f"text exceeds {MAX_TTS_CHARS} chars")
    voice = VOICES.get(voice_id)
    if voice is None:
        raise ValueError(f"unknown voice_id: {voice_id!r}")

    # Primary
    edge_error: Exception | None = None
    try:
        audio = await _synthesize_edge_tts(text, voice)
        return SynthesisResult(
            audio=audio,
            mime_type="audio/mpeg",
            voice=voice,
            fallback_used=False,
        )
    except Exception as exc:  # noqa: BLE001
        edge_error = exc
        logger.warning(
            "edge-tts failed for voice=%s: %s — trying Piper",
            voice_id,
            exc,
        )

    # Fallback
    try:
        audio = await _synthesize_piper(text, voice)
        return SynthesisResult(
            audio=audio,
            mime_type="audio/wav",
            voice=voice,
            fallback_used=True,
        )
    except Exception as piper_error:  # noqa: BLE001
        logger.error(
            "all TTS engines failed for voice=%s; edge=%s; piper=%s",
            voice_id,
            edge_error,
            piper_error,
        )
        raise TTSError(
            f"all TTS engines failed (edge: {edge_error}; piper: {piper_error})"
        ) from piper_error
