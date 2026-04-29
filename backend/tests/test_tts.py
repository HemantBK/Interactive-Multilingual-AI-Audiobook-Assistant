"""TTS service — fallback chain, validation, content_hash. Engines are mocked
since edge-tts is a network call and Piper voices aren't shipped yet."""

from __future__ import annotations

import pytest

from app.services import tts as tts_module
from app.services.tts import TTSError, content_hash, synthesize
from app.services.voices import VOICES

# ---------- content_hash ----------


def test_content_hash_is_deterministic() -> None:
    a = content_hash("hello", "en-female")
    b = content_hash("hello", "en-female")
    assert a == b
    assert len(a) == 64


def test_content_hash_changes_with_text() -> None:
    assert content_hash("hello", "en-female") != content_hash("Hello", "en-female")


def test_content_hash_changes_with_voice() -> None:
    assert content_hash("hello", "en-female") != content_hash("hello", "hi-female")


def test_content_hash_works_on_indic_text() -> None:
    out = content_hash("नमस्ते दुनिया", "hi-female")
    assert len(out) == 64


# ---------- input validation ----------


@pytest.mark.asyncio
async def test_synthesize_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        await synthesize("", "en-female")


@pytest.mark.asyncio
async def test_synthesize_rejects_whitespace_only() -> None:
    with pytest.raises(ValueError):
        await synthesize("    \n\t ", "en-female")


@pytest.mark.asyncio
async def test_synthesize_rejects_oversize_text() -> None:
    with pytest.raises(ValueError):
        await synthesize("a" * (tts_module.MAX_TTS_CHARS + 1), "en-female")


@pytest.mark.asyncio
async def test_synthesize_rejects_unknown_voice_id() -> None:
    with pytest.raises(ValueError):
        await synthesize("hello", "xx-female")


# ---------- fallback chain ----------


@pytest.mark.asyncio
async def test_synthesize_returns_edge_tts_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_edge(text: str, voice):
        assert text == "hello"
        return b"fake mp3 audio"

    monkeypatch.setattr(tts_module, "_synthesize_edge_tts", fake_edge)

    result = await synthesize("hello", "en-female")
    assert result.audio == b"fake mp3 audio"
    assert result.mime_type == "audio/mpeg"
    assert result.fallback_used is False
    assert result.voice == VOICES["en-female"]


@pytest.mark.asyncio
async def test_synthesize_falls_back_to_piper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def edge_fails(text: str, voice):
        raise RuntimeError("edge-tts WebSocket dropped")

    async def piper_works(text: str, voice):
        return b"fake wav audio"

    monkeypatch.setattr(tts_module, "_synthesize_edge_tts", edge_fails)
    monkeypatch.setattr(tts_module, "_synthesize_piper", piper_works)

    result = await synthesize("hello", "hi-female")
    assert result.audio == b"fake wav audio"
    assert result.mime_type == "audio/wav"
    assert result.fallback_used is True


@pytest.mark.asyncio
async def test_synthesize_raises_when_both_engines_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def edge_fails(text: str, voice):
        raise RuntimeError("edge down")

    async def piper_fails(text: str, voice):
        raise TTSError("Piper not loaded")

    monkeypatch.setattr(tts_module, "_synthesize_edge_tts", edge_fails)
    monkeypatch.setattr(tts_module, "_synthesize_piper", piper_fails)

    with pytest.raises(TTSError) as exc:
        await synthesize("hello", "en-female")
    # Both upstream failures should be referenced for triage
    assert "edge" in str(exc.value).lower()
    assert "piper" in str(exc.value).lower()
