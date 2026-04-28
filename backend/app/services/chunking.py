"""
Indic-aware recursive character chunking with bbox aggregation.

Splits per page (so a chunk never spans pages) using a separator hierarchy
that respects Indic sentence boundaries:
  ¶ \\n\\n → ॥ → । → \\n → ". " → "? " → "! " → "; " → ", " → " " → ""

। (U+0964 danda) and ॥ (U+0965 double danda) terminate Hindi/Bengali/Marathi/
Sanskrit sentences and verses. Latin punctuation comes lower in the
hierarchy because most Indic source uses it for parenthetical asides only.

Chunks carry citation anchors (page_number, char_start, char_end) and the
union of word bboxes whose offsets fall inside the chunk's char range.
500-char chunks with 50-char overlap (build plan A2 §2).
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.extraction import ExtractedDocument, ExtractedPage, WordBox

CHUNK_CHAR_SIZE = 500
CHUNK_CHAR_OVERLAP = 50

INDIC_AWARE_SEPARATORS: list[str] = [
    "\n\n",
    "॥",
    "।",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
    "",
]


@dataclass
class Chunk:
    chunk_index: int
    text: str
    page_number: int
    char_start: int
    char_end: int
    bbox: list[dict[str, float | int]] | None  # [{page,x0,y0,x1,y1}, ...]


def _walk_word_offsets(
    page_text: str, page_words: list[WordBox]
) -> list[tuple[int, int, WordBox]]:
    """
    Map each word to (start, end) char offset in page_text by sequential
    matching. Walks a cursor forward — handles repeated tokens like 'the'
    correctly. Returns at most len(page_words) entries; words not found are
    skipped (rare; usually whitespace drift after normalization).
    """
    out: list[tuple[int, int, WordBox]] = []
    cursor = 0
    for w in page_words:
        if not w.text:
            continue
        idx = page_text.find(w.text, cursor)
        if idx < 0:
            continue
        end = idx + len(w.text)
        out.append((idx, end, w))
        cursor = end
    return out


def _bboxes_for_range(
    word_offsets: list[tuple[int, int, WordBox]],
    chunk_start: int,
    chunk_end: int,
    page_number: int,
) -> list[dict[str, float | int]]:
    boxes: list[dict[str, float | int]] = []
    for start, end, w in word_offsets:
        if end <= chunk_start:
            continue
        if start >= chunk_end:
            break  # word_offsets is sorted; we can stop
        boxes.append(
            {
                "page": page_number,
                "x0": w.x0,
                "y0": w.y0,
                "x1": w.x1,
                "y1": w.y1,
            }
        )
    return boxes


def chunk_document(doc: ExtractedDocument) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_CHAR_SIZE,
        chunk_overlap=CHUNK_CHAR_OVERLAP,
        separators=INDIC_AWARE_SEPARATORS,
        keep_separator=True,
    )

    chunks: list[Chunk] = []
    chunk_index = 0
    seen_text_hashes: set[str] = set()

    for page in doc.pages:
        if not page.text.strip():
            continue

        word_offsets = _walk_word_offsets(page.text, page.words) if page.words else []

        for piece in splitter.split_text(page.text):
            piece = piece.strip()
            if len(piece) < 30:  # skip tiny noise fragments
                continue

            # Defensive dedup — boilerplate strip should have caught most of this
            piece_key = piece[:200]
            if piece_key in seen_text_hashes:
                continue
            seen_text_hashes.add(piece_key)

            offset = page.text.find(piece)
            if offset < 0:
                offset = 0
            end = offset + len(piece)
            bboxes = (
                _bboxes_for_range(word_offsets, offset, end, page.page_number)
                if word_offsets
                else []
            )
            chunks.append(
                Chunk(
                    chunk_index=chunk_index,
                    text=piece,
                    page_number=page.page_number,
                    char_start=offset,
                    char_end=end,
                    bbox=bboxes if bboxes else None,
                )
            )
            chunk_index += 1

    return chunks
