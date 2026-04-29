"""HTTP-level smoke tests for /tts and /voices."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

# ---------- /voices ----------


def test_voices_requires_token() -> None:
    client = TestClient(app)
    res = client.get("/voices")
    assert res.status_code == 401


def test_voices_rejects_garbage_token() -> None:
    client = TestClient(app)
    res = client.get("/voices", headers={"Authorization": "Bearer not-real"})
    assert res.status_code == 401


# ---------- /tts ----------


def test_tts_requires_token() -> None:
    client = TestClient(app)
    res = client.post("/tts", json={"text": "hello", "voice_id": "en-female"})
    assert res.status_code == 401


def test_tts_rejects_garbage_token() -> None:
    client = TestClient(app)
    res = client.post(
        "/tts",
        headers={"Authorization": "Bearer not-real"},
        json={"text": "hello", "voice_id": "en-female"},
    )
    assert res.status_code == 401


def test_tts_validates_empty_text() -> None:
    client = TestClient(app)
    res = client.post(
        "/tts",
        headers={"Authorization": "Bearer fake"},
        json={"text": "", "voice_id": "en-female"},
    )
    assert res.status_code in (401, 422)


def test_tts_validates_oversize_text() -> None:
    client = TestClient(app)
    res = client.post(
        "/tts",
        headers={"Authorization": "Bearer fake"},
        json={"text": "a" * 5000, "voice_id": "en-female"},
    )
    assert res.status_code in (401, 422)


def test_tts_validates_voice_id_length() -> None:
    client = TestClient(app)
    res = client.post(
        "/tts",
        headers={"Authorization": "Bearer fake"},
        json={"text": "hello", "voice_id": "x"},
    )
    assert res.status_code in (401, 422)
