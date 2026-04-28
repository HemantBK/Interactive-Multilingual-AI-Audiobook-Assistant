"""Voice catalog — pure-function tests."""

from __future__ import annotations

from app.services.voices import (
    VOICES,
    default_voice_for_language,
    voices_for_language,
)


def test_priority_indic_languages_have_voices() -> None:
    for lang in ["en", "hi", "ta", "bn", "mr", "te"]:
        female = f"{lang}-female"
        male = f"{lang}-male"
        assert female in VOICES, f"missing {female}"
        assert male in VOICES, f"missing {male}"


def test_voice_ids_match_their_internal_id() -> None:
    for vid, spec in VOICES.items():
        assert spec.voice_id == vid


def test_engine_is_edge_tts_for_v1() -> None:
    # Day 21 wires Piper variants. Until then everyone uses edge-tts.
    for spec in VOICES.values():
        assert spec.engine == "edge-tts"


def test_default_voice_falls_back_to_english_for_unknown_language() -> None:
    assert default_voice_for_language("xx").language == "en"
    assert default_voice_for_language(None).language == "en"
    assert default_voice_for_language("").language == "en"


def test_default_voice_picks_indic_when_available() -> None:
    assert default_voice_for_language("hi").voice_id == "hi-female"
    assert default_voice_for_language("ta").voice_id == "ta-female"


def test_voices_for_language_returns_pair() -> None:
    hi_voices = voices_for_language("hi")
    assert len(hi_voices) == 2
    assert {v.gender for v in hi_voices} == {"female", "male"}


def test_voices_for_unknown_language_is_empty() -> None:
    assert voices_for_language("xx") == []
