"""KILL_SWITCH middleware — gated paths return 503; meta paths still work."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import config as config_module
from app.main import app


@pytest.fixture
def kill_switch_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config_module.settings, "kill_switch", True)
    yield


def test_health_works_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200


def test_root_works_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200


def test_rag_blocked_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        headers={"Authorization": "Bearer fake"},
        json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "question": "anything",
        },
    )
    assert res.status_code == 503
    assert res.json()["code"] == "kill_switch_active"


def test_tts_blocked_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.post(
        "/tts",
        headers={"Authorization": "Bearer fake"},
        json={"text": "hello", "voice_id": "en-female"},
    )
    assert res.status_code == 503


def test_translate_blocked_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.post(
        "/translate",
        headers={"Authorization": "Bearer fake"},
        json={"text": "hello", "target_language": "hi"},
    )
    assert res.status_code == 503


def test_documents_post_blocked_with_kill_switch_on(kill_switch_on) -> None:
    client = TestClient(app)
    res = client.post(
        "/documents",
        headers={
            "Authorization": "Bearer fake",
            "Idempotency-Key": "00000000-0000-0000-0000-000000000000",
        },
        files={"file": ("a.pdf", b"%PDF-1.4\n", "application/pdf")},
        data={"title": "x"},
    )
    assert res.status_code == 503


def test_documents_get_works_with_kill_switch_on(kill_switch_on) -> None:
    """Read-only document fetches should keep working when AI is disabled."""
    client = TestClient(app)
    res = client.get(
        "/documents",
        headers={"Authorization": "Bearer fake"},
    )
    # 401 from auth (we passed a fake token) — NOT 503 from kill switch.
    assert res.status_code == 401


def test_kill_switch_off_does_not_gate() -> None:
    """When kill_switch=False, requests pass through to normal handling."""
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        headers={"Authorization": "Bearer fake"},
        json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "question": "anything",
        },
    )
    # Reaches auth → 401, not 503.
    assert res.status_code == 401
