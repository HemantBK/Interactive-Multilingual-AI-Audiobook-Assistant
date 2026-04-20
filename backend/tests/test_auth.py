from fastapi.testclient import TestClient

from app.main import app


def test_me_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token() -> None:
    client = TestClient(app)
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
