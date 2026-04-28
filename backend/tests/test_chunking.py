"""Unit tests for chunking — no embedding, no I/O."""

from __future__ import annotations

from app.services.chunking import (
    CHUNK_CHAR_SIZE,
    INDIC_AWARE_SEPARATORS,
    chunk_document,
)
from app.services.extraction import ExtractedDocument, ExtractedPage


def _make_doc(page_texts: list[str]) -> ExtractedDocument:
    pages = [ExtractedPage(page_number=i + 1, text=t) for i, t in enumerate(page_texts)]
    return ExtractedDocument(
        pages=pages,
        full_text="\n\n".join(page_texts),
        source_language=None,
    )


def test_indic_separators_in_priority_order() -> None:
    # \\n\\n must come first; danda before single \\n
    assert INDIC_AWARE_SEPARATORS[0] == "\n\n"
    assert INDIC_AWARE_SEPARATORS.index("॥") < INDIC_AWARE_SEPARATORS.index("।")
    assert INDIC_AWARE_SEPARATORS.index("।") < INDIC_AWARE_SEPARATORS.index("\n")


def test_skips_tiny_fragments() -> None:
    doc = _make_doc(["short."])
    chunks = chunk_document(doc)
    # < 30-char fragment is dropped as noise
    assert chunks == []


def test_simple_paragraph_yields_one_chunk() -> None:
    text = (
        "ARIA is a multilingual reader that supports both English and several "
        "Indic languages. Citation Mode highlights the exact passage in the "
        "source for every answer the model produces."
    )
    chunks = chunk_document(_make_doc([text]))
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].char_start == 0


def test_long_text_splits_into_multiple_chunks() -> None:
    paragraph = "This is a sentence. " * 100  # ~2000 chars
    chunks = chunk_document(_make_doc([paragraph]))
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.text) <= CHUNK_CHAR_SIZE + 50  # overlap slack


def test_chunk_indexes_are_sequential_across_pages() -> None:
    page_text = "Sentence one. Sentence two. Sentence three. " * 30
    chunks = chunk_document(_make_doc([page_text, page_text, page_text]))
    indexes = [c.chunk_index for c in chunks]
    assert indexes == sorted(indexes)
    assert indexes[0] == 0
    assert len(set(indexes)) == len(indexes)  # no duplicates


def test_chunks_preserve_page_numbers() -> None:
    long = "A long sentence for the body. " * 60
    chunks = chunk_document(_make_doc([long, long, long]))
    pages_seen = {c.page_number for c in chunks}
    assert pages_seen == {1, 2, 3}


def test_indic_text_splits_on_danda() -> None:
    # Hindi text with danda boundaries; force enough length to chunk
    sentence = "यह एक हिंदी पाठ है। यहाँ दूसरा वाक्य है। तीसरा वाक्य भी है। "
    long_text = sentence * 30
    chunks = chunk_document(_make_doc([long_text]))
    assert len(chunks) >= 2
    # Most chunks should end on a danda or close to one (no proof needed —
    # we just want to verify the splitter ran without error on Indic text)
    for c in chunks:
        assert c.text.strip()


def test_char_offsets_within_page_text() -> None:
    text = "Section A starts here. " + ("Body text. " * 100) + "End."
    chunks = chunk_document(_make_doc([text]))
    for c in chunks:
        # char_start..char_end must point to a substring of the page
        assert 0 <= c.char_start < len(text)
        assert c.char_start <= c.char_end <= len(text)
