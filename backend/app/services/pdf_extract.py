"""
PDF extraction with word-level bounding boxes via pdfplumber (MIT).

pdfplumber chosen over PyMuPDF (AGPL — see ADR 0001). pdfplumber is ~10%
slower on large PDFs but the license tree stays clean.

Bbox convention: (x0, top, x1, bottom) in PDF points. We re-emit as
(x0, y0, x1, y1) where y0=top, y1=bottom. Origin is top-left.
"""

from __future__ import annotations

from io import BytesIO

import pdfplumber

from app.services.extraction import ExtractedDocument, ExtractedPage, WordBox
from app.services.lang_detect import detect_language


def extract_pdf(content: bytes) -> ExtractedDocument:
    pages: list[ExtractedPage] = []
    full_text_parts: list[str] = []

    with pdfplumber.open(BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            words: list[WordBox] = []
            for w in page.extract_words():
                words.append(
                    WordBox(
                        text=w["text"],
                        x0=float(w["x0"]),
                        y0=float(w["top"]),
                        x1=float(w["x1"]),
                        y1=float(w["bottom"]),
                    )
                )
            pages.append(
                ExtractedPage(
                    page_number=i + 1,
                    text=text,
                    words=words,
                    width=float(page.width),
                    height=float(page.height),
                )
            )
            full_text_parts.append(text)

    full_text = "\n\n".join(p for p in full_text_parts if p)
    return ExtractedDocument(
        pages=pages,
        full_text=full_text,
        source_language=detect_language(full_text),
    )
