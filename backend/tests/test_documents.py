"""HTTP-level smoke tests for /documents (auth gate). Full integration tests
that actually upload to Supabase live in tests/integration/ (Day 14)."""

from fastapi.testclient import TestClient

from app.main import app


def _pdf_files() -> dict[str, tuple[str, bytes, str]]:
    return {"file": ("a.pdf", b"%PDF-1.4\nfoo", "application/pdf")}


def test_create_document_requires_token() -> None:
    client = TestClient(app)
    response = client.post(
        "/documents",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000000"},
        files=_pdf_files(),
        data={"title": "x"},
    )
    assert response.status_code == 401


def test_create_document_rejects_garbage_token() -> None:
    client = TestClient(app)
    response = client.post(
        "/documents",
        headers={
            "Authorization": "Bearer not-a-real-token",
            "Idempotency-Key": "00000000-0000-0000-0000-000000000000",
        },
        files=_pdf_files(),
        data={"title": "x"},
    )
    assert response.status_code == 401


def test_create_document_missing_idempotency_header() -> None:
    client = TestClient(app)
    response = client.post(
        "/documents",
        headers={"Authorization": "Bearer fake"},
        files=_pdf_files(),
        data={"title": "x"},
    )
    # Either 401 (auth runs first) or 422 (Header validation runs first) —
    # both reject the request before anything writes. We only assert that
    # the request is not allowed through.
    assert response.status_code in (401, 422)
