"""
OpenAPI spec sanity — light-weight contract test that runs in every CI build.

Catches the common drift bugs without needing schemathesis fuzzing:
  - spec is well-formed OpenAPI 3.x
  - all $ref references resolve
  - every declared endpoint has at least one declared response
"""

from __future__ import annotations

import pytest
from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from app.main import app


def test_openapi_is_valid_3_x() -> None:
    spec = app.openapi()
    assert spec["openapi"].startswith("3."), spec["openapi"]
    try:
        validate(spec)
    except OpenAPIValidationError as exc:
        pytest.fail(f"OpenAPI spec is invalid: {exc}")


def test_every_path_has_at_least_one_response() -> None:
    spec = app.openapi()
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.startswith("x-"):  # OpenAPI extensions
                continue
            assert op.get("responses"), f"{method.upper()} {path} declares no responses"


def test_known_endpoints_are_declared() -> None:
    spec = app.openapi()
    paths = set(spec["paths"].keys())
    # Endpoints we shipped in Days 1–12. If one is missing here, either the
    # router isn't registered or its decorator changed silently.
    expected = {
        "/health",
        "/auth/me",
        "/auth/login",
        "/auth/logout",
        "/documents",
        "/documents/{document_id}",
        "/rag/ask",
        "/translate",
        "/tts",
        "/voices",
        "/user/me/export",
        "/user/me",
    }
    missing = expected - paths
    assert not missing, f"missing endpoints in OpenAPI: {missing}"
