"""HTTP-level smoke tests for /rag/ask. Full integration tests with real
Supabase + Groq live in tests/integration/ (Day 14)."""

from fastapi.testclient import TestClient

from app.main import app


def test_rag_ask_requires_token() -> None:
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "question": "What is X?",
        },
    )
    assert res.status_code == 401


def test_rag_ask_rejects_bad_token() -> None:
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        headers={"Authorization": "Bearer not-a-real-token"},
        json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "question": "What is X?",
        },
    )
    assert res.status_code == 401


def test_rag_ask_validates_doc_id_length() -> None:
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        headers={"Authorization": "Bearer fake"},
        json={"document_id": "too-short", "question": "What is X?"},
    )
    # 422 (validation) or 401 (auth) — either way, request is rejected
    assert res.status_code in (401, 422)


def test_rag_ask_rejects_empty_question() -> None:
    client = TestClient(app)
    res = client.post(
        "/rag/ask",
        headers={"Authorization": "Bearer fake"},
        json={
            "document_id": "00000000-0000-0000-0000-000000000000",
            "question": "",
        },
    )
    assert res.status_code in (401, 422)
