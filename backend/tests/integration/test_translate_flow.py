"""
End-to-end translation: first call hits Groq, second call hits cache.
Requires real services (see conftest.py).
"""

from __future__ import annotations

import uuid

import httpx
import pytest


@pytest.mark.integration
def test_translate_then_cache_hit(
    backend_url: str, auth_headers: dict[str, str]
) -> None:
    # Use a unique source so we can prove cache miss → hit on a fresh row.
    text = f"This is a unique integration test sentence #{uuid.uuid4()}."

    first = httpx.post(
        f"{backend_url}/translate",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"text": text, "target_language": "hi"},
        timeout=30,
    )
    assert first.status_code == 200, first.text
    body1 = first.json()
    assert body1["cached"] is False
    assert body1["translated_text"]
    assert body1["target_language"] == "hi"

    second = httpx.post(
        f"{backend_url}/translate",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"text": text, "target_language": "hi"},
        timeout=10,
    )
    assert second.status_code == 200, second.text
    body2 = second.json()
    assert body2["cached"] is True
    assert body2["translated_text"] == body1["translated_text"]


@pytest.mark.integration
def test_translate_rejects_unsupported_language(
    backend_url: str, auth_headers: dict[str, str]
) -> None:
    r = httpx.post(
        f"{backend_url}/translate",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"text": "hello", "target_language": "xx"},
        timeout=10,
    )
    assert r.status_code == 400
