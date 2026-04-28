"""Prompt assembly — pure-function tests."""

from __future__ import annotations

from app.services.prompts import (
    PROMPT_ID,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_rag_prompt,
)


def test_prompt_identity_is_stable() -> None:
    # Sanity: id+version are constants used by Day 9 to register in DB.
    assert PROMPT_ID == "rag.system"
    assert PROMPT_VERSION == 1


def test_system_prompt_has_anti_injection_rule() -> None:
    assert "untrusted" in SYSTEM_PROMPT.lower()
    assert "never follow instructions" in SYSTEM_PROMPT.lower()


def test_system_prompt_specifies_json_schema() -> None:
    assert "answer" in SYSTEM_PROMPT
    assert "citations" in SYSTEM_PROMPT
    assert "chunk_id" in SYSTEM_PROMPT
    assert "quote" in SYSTEM_PROMPT


def test_build_rag_prompt_shape() -> None:
    chunks = [
        {"id": 7, "page_number": 3, "text": "Photosynthesis converts sunlight."},
        {"id": 11, "page_number": 4, "text": "Chlorophyll absorbs light."},
    ]
    msgs = build_rag_prompt("How do plants make food?", chunks)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    body = msgs[1]["content"]
    assert "<chunk id=\"7\"" in body
    assert "<chunk id=\"11\"" in body
    assert "Photosynthesis" in body
    assert "How do plants make food?" in body


def test_build_rag_prompt_handles_empty_chunks() -> None:
    msgs = build_rag_prompt("anything", [])
    assert msgs[1]["content"].count("<chunk") == 0
    assert "anything" in msgs[1]["content"]


def test_build_rag_prompt_includes_page_in_tag() -> None:
    chunks = [{"id": 1, "page_number": 42, "text": "x"}]
    msgs = build_rag_prompt("q", chunks)
    assert 'page="42"' in msgs[1]["content"]
