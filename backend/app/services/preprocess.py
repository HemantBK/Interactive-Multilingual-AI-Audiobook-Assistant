"""
Pre-chunking text cleanup:
  1. Unicode NFC normalize (consistent codepoint sequences for Indic).
  2. Whitespace normalize (collapse runs, trim per line, cap blank lines).
  3. Strip page-number lines and document-wide running headers/footers.

Operates on str, not bytes — Python char indices are preserved through
NFC, so chunk citation offsets remain valid.

Boilerplate detection is per-document (need ≥5 pages for signal). Lines
that appear on ≥60% of pages are treated as headers/footers and removed.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from app.services.extraction import ExtractedDocument, ExtractedPage

_PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?\s*$", re.IGNORECASE
)
_WHITESPACE_RUN = re.compile(r"[ \t]+")
_NEWLINE_RUN = re.compile(r"\n{3,}")

BOILERPLATE_PAGE_THRESHOLD = 5
BOILERPLATE_FREQUENCY = 0.60


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    cleaned_lines = [_WHITESPACE_RUN.sub(" ", line).rstrip() for line in text.splitlines()]
    text = "\n".join(cleaned_lines)
    return _NEWLINE_RUN.sub("\n\n", text)


def _is_page_number_line(line: str) -> bool:
    return bool(_PAGE_NUMBER.match(line))


def _detect_boilerplate_lines(pages: list[ExtractedPage]) -> set[str]:
    if len(pages) < BOILERPLATE_PAGE_THRESHOLD:
        return set()
    counts: Counter[str] = Counter()
    for page in pages:
        seen_on_page = set()
        for line in page.text.splitlines():
            stripped = line.strip()
            if not stripped or len(stripped) > 200:
                continue
            seen_on_page.add(stripped)
        for line in seen_on_page:
            counts[line] += 1
    cutoff = max(3, int(BOILERPLATE_FREQUENCY * len(pages)))
    return {line for line, count in counts.items() if count >= cutoff}


def preprocess(doc: ExtractedDocument) -> ExtractedDocument:
    """
    Return a new ExtractedDocument with cleaned text. Word lists carry over
    unchanged; chunk-time bbox alignment tolerates the text drift introduced
    by normalization (it walks word offsets through the cleaned text).
    """
    pages_normed: list[ExtractedPage] = [
        ExtractedPage(
            page_number=p.page_number,
            text=_normalize_text(p.text),
            words=p.words,
            width=p.width,
            height=p.height,
        )
        for p in doc.pages
    ]

    boilerplate = _detect_boilerplate_lines(pages_normed)

    final_pages: list[ExtractedPage] = []
    for p in pages_normed:
        kept: list[str] = []
        for line in p.text.splitlines():
            stripped = line.strip()
            if not stripped:
                kept.append("")
                continue
            if stripped in boilerplate or _is_page_number_line(stripped):
                kept.append("")
                continue
            kept.append(line)
        final_text = _NEWLINE_RUN.sub("\n\n", "\n".join(kept)).strip("\n")
        final_pages.append(
            ExtractedPage(
                page_number=p.page_number,
                text=final_text,
                words=p.words,
                width=p.width,
                height=p.height,
            )
        )

    full_text = "\n\n".join(p.text for p in final_pages if p.text.strip())
    return ExtractedDocument(
        pages=final_pages,
        full_text=full_text,
        source_language=doc.source_language,
    )
