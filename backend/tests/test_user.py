"""HTTP-level smoke tests for /user/me/export and /user/me."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_export_requires_token() -> None:
    client = TestClient(app)
    res = client.get("/user/me/export")
    assert res.status_code == 401


def test_export_rejects_garbage_token() -> None:
    client = TestClient(app)
    res = client.get(
        "/user/me/export", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert res.status_code == 401


def test_delete_requires_token() -> None:
    client = TestClient(app)
    res = client.delete("/user/me")
    assert res.status_code == 401


def test_delete_rejects_garbage_token() -> None:
    client = TestClient(app)
    res = client.delete(
        "/user/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert res.status_code == 401
