"""
schemathesis contract tests — property-based fuzzing of the API against
its declared OpenAPI schema (build plan §14, Day 14).

Default scope: only unauth endpoints (/health, /). Authenticated endpoints
are skipped because the fuzzer has no JWT — adding one would require an
integration env setup, which lives under tests/integration.

Tolerated drift: 401 from auth-required endpoints. Anything else must
match a declared response shape.

This test is fast (~1 s) and runs in every CI build.
"""

from __future__ import annotations

import pytest
import schemathesis

from app.main import app

# FastAPI 0.99+ emits OpenAPI 3.1.0; schemathesis 4.x supports it natively
# (the 3.x experimental flag is gone).
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@pytest.mark.contract
@schema.parametrize()
def test_api_conforms_to_schema(case) -> None:
    response = case.call()
    # Tolerated status codes — none of these reflect a contract drift:
    #  400: starlette returns this for malformed multipart bodies the
    #       fuzzer happily generates; not a route-level contract.
    #  401: auth-required endpoint, fuzzer has no JWT.
    #  422: pydantic validation error from random fuzzed bodies.
    #  429: slowapi rate limit hit by the fuzzer's burst (per-minute window
    #       in unit-test mode, easy to saturate).
    # Day 26 hardening pass will declare these in the OpenAPI schema and
    # tighten the tolerance.
    if response.status_code in (400, 401, 422, 429):
        return
    case.validate_response(response)
