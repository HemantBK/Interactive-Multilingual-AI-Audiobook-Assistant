"""Tests for the extraction dispatcher + plaintext path."""

from __future__ import annotations

import pytest

from app.services.extraction import extract, extract_plaintext


def test_plaintext_basic() -> None:
    content = b"Hello world. This is a test document.\n\nSecond paragraph here."
    result = extract_plaintext(content)
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert "Hello world" in result.pages[0].text
    assert result.pages[0].words == []
    assert result.full_text == result.pages[0].text


def test_plaintext_indic_detects_hindi() -> None:
    text = "नमस्ते दुनिया, यह एक हिंदी पाठ है। यहाँ दूसरा वाक्य है। तीसरा वाक्य भी।"
    result = extract_plaintext(text.encode("utf-8"))
    assert result.source_language == "hi"


def test_plaintext_short_text_no_lang() -> None:
    result = extract_plaintext(b"hi")
    assert result.source_language is None


def test_dispatch_text_routes_to_plaintext() -> None:
    result = extract(
        b"Plain ASCII test content for source dispatcher routing logic.", "text"
    )
    assert len(result.pages) == 1
    assert "Plain ASCII" in result.pages[0].text


def test_dispatch_unknown_source_type_raises() -> None:
    with pytest.raises(ValueError):
        extract(b"foo", "video")
