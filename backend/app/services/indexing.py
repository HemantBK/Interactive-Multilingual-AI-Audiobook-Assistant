"""
Index a preprocessed document: chunk + embed + persist.

Storage layout:
  - chunks bucket → `<doc_id>/chunks.json` holds ALL chunks of a doc in one
    file, so retrieval downloads ONE blob per doc instead of N. The schema's
    `text_storage_path` column points every chunk row of a doc at this same
    path; the per-row `chunk_index` looks up the entry inside the JSON.
  - document_chunks table → one row per chunk with embedding + citation
    anchors (page_number, char_start, char_end, bbox).

Replays are idempotent: existing chunks for the doc are deleted before
insert, and the JSON blob is upserted.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from supabase import Client

from app.services import storage
from app.services.chunking import chunk_document
from app.services.embedding import MODEL_VERSION, embed_texts
from app.services.extraction import ExtractedDocument
from app.services.preprocess import preprocess

logger = logging.getLogger(__name__)

INSERT_BATCH = 100


def index_document(
    db: Client,
    doc_id: uuid.UUID,
    extracted: ExtractedDocument,
) -> int:
    """Returns chunk count. 0 = doc was empty after preprocess (still 'ready')."""
    doc_id_str = str(doc_id)

    cleaned = preprocess(extracted)
    chunks = chunk_document(cleaned)

    if not chunks:
        logger.info("indexing: no chunks after preprocess (doc=%s)", doc_id_str)
        return 0

    chunks_path = f"{doc_id_str}/chunks.json"
    chunks_blob = json.dumps(
        [{"chunk_index": c.chunk_index, "text": c.text} for c in chunks],
        ensure_ascii=False,
    ).encode("utf-8")
    storage.upload(
        db,
        bucket=storage.BUCKET_CHUNKS,
        path=chunks_path,
        content=chunks_blob,
        content_type="application/json",
        upsert=True,
    )

    vectors = embed_texts([c.text for c in chunks])

    rows: list[dict[str, Any]] = []
    for chunk, vec in zip(chunks, vectors, strict=True):
        rows.append(
            {
                "document_id": doc_id_str,
                "chunk_index": chunk.chunk_index,
                "text_storage_path": chunks_path,
                "page_number": chunk.page_number,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "bbox": chunk.bbox,
                "token_count": len(chunk.text.split()),
                "embedding": vec,
                "embedding_model_version": MODEL_VERSION,
                "lang_detect": cleaned.source_language,
            }
        )

    # Wipe prior chunks (replay safety) then bulk-insert
    db.table("document_chunks").delete().eq("document_id", doc_id_str).execute()
    for i in range(0, len(rows), INSERT_BATCH):
        db.table("document_chunks").insert(rows[i : i + INSERT_BATCH]).execute()

    return len(rows)
