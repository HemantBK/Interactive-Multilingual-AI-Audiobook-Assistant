"""
Image OCR via Tesseract (Apache-2.0).

We pass a multi-language hint covering English + the 5 priority Indic
scripts. Tesseract picks the best fit per word. This is slower than
single-lang but more general — and the source language is what we're
trying to detect, so we can't pre-filter.

Words with confidence < 30 are dropped (Tesseract noise on low-contrast
patches). The cutoff is empirical; tune in eval phase (Day 23).

Coordinate system: image pixel coords, origin top-left.
"""

from __future__ import annotations

from io import BytesIO

import pytesseract
from PIL import Image

from app.services.extraction import ExtractedDocument, ExtractedPage, WordBox
from app.services.lang_detect import detect_language

OCR_LANGS = "eng+hin+tam+ben+mar+tel"
MIN_WORD_CONFIDENCE = 30  # 0–100 scale


def extract_image(content: bytes) -> ExtractedDocument:
    img = Image.open(BytesIO(content))
    img.load()

    data = pytesseract.image_to_data(
        img, lang=OCR_LANGS, output_type=pytesseract.Output.DICT
    )

    words: list[WordBox] = []
    text_parts: list[str] = []
    for i, raw_text in enumerate(data["text"]):
        word_text = (raw_text or "").strip()
        if not word_text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = 0.0
        if conf < MIN_WORD_CONFIDENCE:
            continue
        x = float(data["left"][i])
        y = float(data["top"][i])
        w = float(data["width"][i])
        h = float(data["height"][i])
        words.append(
            WordBox(text=word_text, x0=x, y0=y, x1=x + w, y1=y + h)
        )
        text_parts.append(word_text)

    full_text = " ".join(text_parts)
    page = ExtractedPage(
        page_number=1,
        text=full_text,
        words=words,
        width=float(img.width),
        height=float(img.height),
    )
    return ExtractedDocument(
        pages=[page],
        full_text=full_text,
        source_language=detect_language(full_text),
    )
