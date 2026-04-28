"""
Integration tests — env-gated.

These tests hit REAL Supabase + Groq + Storage. They're skipped by default
unless `RUN_INTEGRATION=1` is set AND the required env vars are present:

  SUPABASE_URL, SUPABASE_SERVICE_KEY     # backend can talk to Supabase
  TEST_USER_TOKEN                        # JWT for a pre-seeded test user
  TEST_BACKEND_URL                       # e.g., http://localhost:7860
  GROQ_API_KEY                           # for /rag/ask + /translate

Get TEST_USER_TOKEN by signing in to the frontend manually and copying
session.access_token from the Supabase JS client (or DevTools Storage).

Run them locally:
  RUN_INTEGRATION=1 pytest tests/integration -v

CI: `e2e-and-a11y` job (frontend) covers the user-facing happy path; this
suite is for backend-only flows that don't go through the UI.
"""

from __future__ import annotations

import os
import pathlib
import uuid
from typing import Final

import pytest

REQUIRED_ENV: Final = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "TEST_USER_TOKEN",
    "TEST_BACKEND_URL",
    "GROQ_API_KEY",
)


def _integration_enabled() -> bool:
    if os.environ.get("RUN_INTEGRATION") != "1":
        return False
    return all(os.environ.get(k) for k in REQUIRED_ENV)


def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    if _integration_enabled():
        return
    skip = pytest.mark.skip(
        reason=f"integration tests require RUN_INTEGRATION=1 and {REQUIRED_ENV}"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


# -- shared fixtures ---------------------------------------------------------


@pytest.fixture
def backend_url() -> str:
    return os.environ["TEST_BACKEND_URL"].rstrip("/")


@pytest.fixture
def access_token() -> str:
    return os.environ["TEST_USER_TOKEN"]


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def fresh_idempotency_key() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """
    Minimal valid PDF bytes — the spec's smallest legal file. Tesseract /
    pdfplumber treat this as a single empty page; just enough to exercise
    upload + extraction without shipping a real fixture.
    """
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f\n"
        b"0000000009 00000 n\n"
        b"0000000052 00000 n\n"
        b"0000000098 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n149\n%%EOF\n"
    )


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"
