"""
Voice catalog — maps stable internal voice IDs to engine-specific names.

Internal IDs are language-coded (`en-female`, `hi-male`, etc.) so the
frontend picks by language and gender without knowing whether edge-tts or
Piper is serving the request.

Engine selection is decided per request inside tts.synthesize(), using
edge-tts as primary and Piper as the license-clean fallback (build plan §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

Engine = Literal["edge-tts", "piper"]


@dataclass(frozen=True)
class VoiceSpec:
    voice_id: str           # stable internal ID (e.g., "hi-female")
    language: str           # ISO 639-1 (e.g., "hi")
    label: str              # display name (native script)
    gender: Literal["female", "male"]
    engine: Engine
    engine_voice: str       # name as the engine knows it


# Priority voices for the 6 languages we ship from Day 1 (en, hi, ta, bn, mr, te).
# Edge-TTS Indic Neural voices are the moat (A2 moat: native-quality Indic TTS).
# Day 21 polish wires Piper variants for the same set (license-clean fallback).
VOICES: Final[dict[str, VoiceSpec]] = {
    "en-female": VoiceSpec("en-female", "en", "English — Aria",
                           "female", "edge-tts", "en-US-AriaNeural"),
    "en-male":   VoiceSpec("en-male",   "en", "English — Guy",
                           "male",   "edge-tts", "en-US-GuyNeural"),
    "hi-female": VoiceSpec("hi-female", "hi", "हिन्दी — स्वरा",
                           "female", "edge-tts", "hi-IN-SwaraNeural"),
    "hi-male":   VoiceSpec("hi-male",   "hi", "हिन्दी — मधुर",
                           "male",   "edge-tts", "hi-IN-MadhurNeural"),
    "ta-female": VoiceSpec("ta-female", "ta", "தமிழ் — பல்லவி",
                           "female", "edge-tts", "ta-IN-PallaviNeural"),
    "ta-male":   VoiceSpec("ta-male",   "ta", "தமிழ் — வள்ளுவர்",
                           "male",   "edge-tts", "ta-IN-ValluvarNeural"),
    "bn-female": VoiceSpec("bn-female", "bn", "বাংলা — তানিশা",
                           "female", "edge-tts", "bn-IN-TanishaaNeural"),
    "bn-male":   VoiceSpec("bn-male",   "bn", "বাংলা — ভাস্কর",
                           "male",   "edge-tts", "bn-IN-BashkarNeural"),
    "mr-female": VoiceSpec("mr-female", "mr", "मराठी — आरोही",
                           "female", "edge-tts", "mr-IN-AarohiNeural"),
    "mr-male":   VoiceSpec("mr-male",   "mr", "मराठी — मनोहर",
                           "male",   "edge-tts", "mr-IN-ManoharNeural"),
    "te-female": VoiceSpec("te-female", "te", "తెలుగు — శ్రుతి",
                           "female", "edge-tts", "te-IN-ShrutiNeural"),
    "te-male":   VoiceSpec("te-male",   "te", "తెలుగు — మోహన్",
                           "male",   "edge-tts", "te-IN-MohanNeural"),
}


def default_voice_for_language(language_code: str | None) -> VoiceSpec:
    """Return a sensible default voice for a 2-letter ISO code, falling back to en."""
    if language_code:
        fid = f"{language_code}-female"
        if fid in VOICES:
            return VOICES[fid]
    return VOICES["en-female"]


def voices_for_language(language_code: str) -> list[VoiceSpec]:
    """All voices for a given language code (one female + one male in our catalog)."""
    return [v for v in VOICES.values() if v.language == language_code]
