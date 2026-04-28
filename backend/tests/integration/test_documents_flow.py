"""
End-to-end document flow: upload → poll until ready → ask a question.
Requires real services (see conftest.py).
"""

from __future__ import annotations

import time

import httpx
import pytest


@pytest.mark.integration
def test_health_endpoint_reachable(backend_url: str) -> None:
    r = httpx.get(f"{backend_url}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.integration
def test_upload_index_query_flow(
    backend_url: str,
    auth_headers: dict[str, str],
    fresh_idempotency_key: str,
    sample_pdf_bytes: bytes,
) -> None:
    # 1. Upload
    upload = httpx.post(
        f"{backend_url}/documents",
        headers={**auth_headers, "Idempotency-Key": fresh_idempotency_key},
        files={"file": ("integration.pdf", sample_pdf_bytes, "application/pdf")},
        data={"title": "integration test sample"},
        timeout=60,
    )
    assert upload.status_code == 201, upload.text
    doc_id = upload.json()["document_id"]

    # 2. Poll for ready / failed (cap 90 s — bge-m3 cold start can be slow)
    final_status: str | None = None
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        r = httpx.get(
            f"{backend_url}/documents/{doc_id}", headers=auth_headers, timeout=10
        )
        assert r.status_code == 200, r.text
        final_status = r.json()["status"]
        if final_status in ("ready", "failed"):
            break
        time.sleep(2)
    assert final_status == "ready", f"indexing ended in status={final_status}"

    # 3. RAG ask. The fixture PDF is empty, so the model should report
    # "I don't have enough information." That's still a valid streamed flow.
    with httpx.stream(
        "POST",
        f"{backend_url}/rag/ask",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"document_id": doc_id, "question": "What does this document say?"},
        timeout=60,
    ) as r:
        assert r.status_code == 200, r.read()
        events_seen = []
        for line in r.iter_lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            events_seen.append(line)
            if '"event":"done"' in line or '"event":"error"' in line:
                break

    assert any('"event":"start"' in line for line in events_seen)
    # Either an answer event OR an error — both are valid for an empty doc;
    # what we want to verify is the SSE protocol is well-formed.
    assert any(
        '"event":"answer"' in line or '"event":"error"' in line for line in events_seen
    )
