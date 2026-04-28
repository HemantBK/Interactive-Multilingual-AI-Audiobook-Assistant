"""Unit tests for preprocessing — pure-function, no I/O."""

from __future__ import annotations

import unicodedata

from app.services.extraction import ExtractedDocument, ExtractedPage
from app.services.preprocess import preprocess


def _make_doc(page_texts: list[str]) -> ExtractedDocument:
    pages = [ExtractedPage(page_number=i + 1, text=t) for i, t in enumerate(page_texts)]
    return ExtractedDocument(
        pages=pages,
        full_text="\n\n".join(page_texts),
        source_language=None,
    )


def test_nfc_normalizes_decomposed_devanagari() -> None:
    decomposed = "क़"  # ka + nukta
    page_text = decomposed * 30 + " text"
    doc = _make_doc([page_text])
    result = preprocess(doc)
    # Output should be NFC; round-tripping through NFC must be a no-op
    assert result.pages[0].text == unicodedata.normalize("NFC", result.pages[0].text)


def test_collapses_multiple_spaces() -> None:
    doc = _make_doc(["This  has    extra   spaces between words for testing."])
    result = preprocess(doc)
    assert "  " not in result.pages[0].text


def test_caps_runaway_blank_lines() -> None:
    doc = _make_doc(["Para one.\n\n\n\n\n\nPara two."])
    result = preprocess(doc)
    assert "\n\n\n" not in result.pages[0].text


def test_strips_page_numbers() -> None:
    doc = _make_doc(
        [
            "Real content here for the body of the document about something.\n"
            "Page 1 of 10\n"
            "More body content that is sufficiently long to be retained.",
        ]
    )
    result = preprocess(doc)
    assert "Page 1 of 10" not in result.pages[0].text
    assert "Real content here" in result.pages[0].text


def test_strips_running_header_across_pages() -> None:
    boilerplate = "Confidential — ARIA Internal"
    pages = [
        f"{boilerplate}\nUnique content for page {i} that is long enough to be kept after preprocess."
        for i in range(8)
    ]
    doc = _make_doc(pages)
    result = preprocess(doc)
    for p in result.pages:
        assert boilerplate not in p.text
        assert "Unique content" in p.text


def test_does_not_strip_in_short_docs() -> None:
    # 3-page doc — too few pages to detect boilerplate reliably
    line = "Header text"
    doc = _make_doc([f"{line}\nbody {i}" for i in range(3)])
    result = preprocess(doc)
    assert any(line in p.text for p in result.pages)
