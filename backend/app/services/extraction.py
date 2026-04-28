"""
Document extraction — unified ExtractedDocument across PDF / image / text.

Three back-ends (split into separate modules so we don't force-import
pdfplumber + pytesseract on every cold start):

  pdf  → app.services.pdf_extract  (pdfplumber, word bboxes)
  image→ app.services.ocr           (Tesseract, word bboxes + conf filter)
  text → extract_plaintext below   (UTF-8 decode, no bbox)

Coordinates:
  - PDFs: PDF user-space points (origin top-left, 1 pt = 1/72 inch).
  - Images: pixel coords from the OCR'd image (origin top-left).
  - Text: no bboxes; words list is empty.

These dataclasses are internal only — they don't cross the wire. API-facing
schemas live in app/models/schemas.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.lang_detect import detect_language


@dataclass
class WordBox:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    text: str
    words: list[WordBox] = field(default_factory=list)
    width: float | None = None
    height: float | None = None


@dataclass
class ExtractedDocument:
    pages: list[ExtractedPage]
    full_text: str
    source_language: str | None


def extract_plaintext(content: bytes) -> ExtractedDocument:
    """text/plain — single synthetic page, no bbox info."""
    text = content.decode("utf-8", errors="replace")
    pages = [ExtractedPage(page_number=1, text=text)]
    return ExtractedDocument(
        pages=pages,
        full_text=text,
        source_language=detect_language(text),
    )


def extract(content: bytes, source_type: str) -> ExtractedDocument:
    """Dispatch to the right extractor based on validated source_type."""
    if source_type == "pdf":
        from app.services.pdf_extract import extract_pdf

        return extract_pdf(content)
    if source_type == "image":
        from app.services.ocr import extract_image

        return extract_image(content)
    if source_type == "text":
        return extract_plaintext(content)
    raise ValueError(f"unsupported source_type: {source_type!r}")
