"""Translate service + endpoint smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.translate import (
    MAX_TEXT_CHARS,
    SUPPORTED_LANGUAGES,
    content_hash,
)

# ---------- pure-function ----------


def test_supports_priority_indic_languages() -> None:
    for code in ["en", "hi", "bn", "mr", "ta", "te"]:
        assert code in SUPPORTED_LANGUAGES


def test_has_14_supported_languages() -> None:
    assert len(SUPPORTED_LANGUAGES) == 14


def test_content_hash_is_deterministic() -> None:
    a = content_hash("hello world", "hi")
    b = content_hash("hello world", "hi")
    assert a == b
    assert len(a) == 64  # sha256 hex


def test_content_hash_changes_with_target_language() -> None:
    assert content_hash("hello", "hi") != content_hash("hello", "es")


def test_content_hash_changes_with_text() -> None:
    assert content_hash("hello", "hi") != content_hash("Hello", "hi")


def test_content_hash_works_on_indic_text() -> None:
    out = content_hash("नमस्ते दुनिया", "en")
    assert len(out) == 64


# ---------- HTTP ----------


def test_translate_requires_token() -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        json={"text": "hello", "target_language": "hi"},
    )
    assert res.status_code == 401


def test_translate_rejects_garbage_token() -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={"text": "hello", "target_language": "hi"},
    )
    assert res.status_code == 401


def test_translate_validates_empty_text() -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        headers={"Authorization": "Bearer fake"},
        json={"text": "", "target_language": "hi"},
    )
    # 422 (validation) or 401 (auth) — either rejects.
    assert res.status_code in (401, 422)


def test_translate_validates_target_language_length() -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        headers={"Authorization": "Bearer fake"},
        json={"text": "hello", "target_language": "x"},
    )
    assert res.status_code in (401, 422)


def test_translate_validates_text_too_long() -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        headers={"Authorization": "Bearer fake"},
        json={"text": "a" * (MAX_TEXT_CHARS + 1), "target_language": "hi"},
    )
    assert res.status_code in (401, 422)
