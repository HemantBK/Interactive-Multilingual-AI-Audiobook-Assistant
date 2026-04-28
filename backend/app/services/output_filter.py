"""
Best-effort filter on LLM-generated text (build plan A2 §6).

We watch for two classes of badness in model output:

  1. SOFT — observed pattern that may need triage but isn't an emergency.
            Logged, NOT rewritten. Examples: URLs to non-allowlisted
            domains, suspicious "as an AI..." disclaimers.

  2. HARD — pattern that must NOT reach the user. Replaced with a generic
            rejection. Examples: credential-shaped strings, <script>
            tags, javascript: URLs, raw private keys.

Why hard-replace instead of redact? A surgical redact ("[REDACTED]")
implies we trust the rest of the string, but the same generation that
produced the bad token may have other smuggled content. Replacing the
whole answer is the conservative choice for v1.

Day 26 hardening pass will run this list against the full eval set and
tune the patterns based on real Groq behavior.
"""

from __future__ import annotations

import re
from typing import Final

# ----------------------------------------------------------------------------
# HARD patterns — match → reject the whole answer
# ----------------------------------------------------------------------------

# Common API-key shapes we never want to emit, even if a malicious chunk
# tried to get the model to echo one back.
_CREDENTIAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),                 # OpenAI / generic
    re.compile(r"\bgsk_[A-Za-z0-9_\-]{20,}\b"),                # Groq
    re.compile(r"\bxoxb-[A-Za-z0-9\-]{20,}\b"),                # Slack bot
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS access-key id
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),                       # AWS STS
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),                   # GitHub PAT
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),          # PEM keys
    re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"),  # JWT
)

_HTML_DANGEROUS = re.compile(
    r"<\s*(script|iframe|object|embed|style|link|meta)\b", re.IGNORECASE
)
_JS_URL = re.compile(r"javascript\s*:", re.IGNORECASE)
_DATA_URL_SCRIPT = re.compile(r"data\s*:\s*text/html", re.IGNORECASE)

# ----------------------------------------------------------------------------
# SOFT patterns — log only
# ----------------------------------------------------------------------------

# Allowed URL hosts that may legitimately appear in an answer.
# v1: empty — we never want emitted URLs. Citations are by chunk_id, not URL.
_ALLOWED_DOMAINS: Final[frozenset[str]] = frozenset()

_URL_PATTERN = re.compile(
    r"https?://([\w\-.]+)(?:[/:?#][^\s)<>'\"]*)?", re.IGNORECASE
)

# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

SAFETY_REJECTION_MESSAGE: Final = (
    "I can't share that answer — the model produced content that may be "
    "unsafe (credentials, executable markup, or similar). Please rephrase."
)


def scan_output(text: str) -> tuple[list[str], bool]:
    """Return (findings, is_safe). is_safe=False → caller must replace text."""
    findings: list[str] = []
    safe = True

    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(text):
            findings.append("credential_pattern")
            safe = False
            break

    if _HTML_DANGEROUS.search(text):
        findings.append("html_dangerous_tag")
        safe = False

    if _JS_URL.search(text):
        findings.append("javascript_url")
        safe = False

    if _DATA_URL_SCRIPT.search(text):
        findings.append("data_url_html")
        safe = False

    # Soft signals
    for match in _URL_PATTERN.finditer(text):
        domain = match.group(1).lower()
        if not any(
            domain == allowed or domain.endswith("." + allowed)
            for allowed in _ALLOWED_DOMAINS
        ):
            findings.append(f"unknown_url:{domain}")

    return findings, safe


def filter_answer(text: str) -> tuple[str, list[str]]:
    """
    Return (clean_text, findings).
    If any HARD pattern matched, clean_text is the rejection message.
    SOFT findings are logged by the caller but text passes through.
    """
    findings, safe = scan_output(text)
    if not safe:
        return SAFETY_REJECTION_MESSAGE, findings
    return text, findings
