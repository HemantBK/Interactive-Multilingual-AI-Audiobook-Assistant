"""
End-to-end indexing pipeline.

  queued → processing → extract → preprocess → chunk → embed → index → ready
                                                                     ↘ failed

CPU-bound work (pdfplumber, Tesseract, bge-m3) runs via asyncio.to_thread
so the FastAPI event loop stays responsive for /health and other reads
while a doc is being indexed. On HF Spaces' single worker, only one
indexing job runs at a time — surplus uploads sit in the documents table
with status='queued' (build plan A2 §2 documents the limit).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.db.supabase import user_client
from app.services import storage
from app.services.extraction import extract
from app.services.indexing import index_document

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_indexing(doc_id: uuid.UUID, access_token: str) -> None:
    """Background task entry point. Drives a queued document to 'ready' or 'failed'."""
    doc_id_str = str(doc_id)
    db = user_client(access_token)

    try:
        # FSM: queued → processing (only if currently 'queued')
        db.table("documents").update({"status": "processing"}).eq(
            "id", doc_id_str
        ).eq("status", "queued").execute()

        result = (
            db.table("documents")
            .select("storage_path, source_type")
            .eq("id", doc_id_str)
            .limit(1)
            .execute()
        )
        if not result.data:
            logger.warning("indexing: doc %s vanished", doc_id_str)
            return
        doc = result.data[0]

        contents = await asyncio.to_thread(
            storage.download, db, storage.BUCKET_DOCUMENTS, doc["storage_path"]
        )

        extracted = await asyncio.to_thread(extract, contents, doc["source_type"])

        db.table("documents").update(
            {
                "page_count": len(extracted.pages),
                "source_language": extracted.source_language,
            }
        ).eq("id", doc_id_str).execute()

        # Chunk + embed + persist (CPU-heavy: bge-m3 inference on CPU)
        chunk_count = await asyncio.to_thread(index_document, db, doc_id, extracted)

        # FSM: processing → ready
        db.table("documents").update(
            {"status": "ready", "processed_at": _now_iso()}
        ).eq("id", doc_id_str).execute()

        logger.info(
            "indexed doc=%s pages=%d chunks=%d lang=%s",
            doc_id_str,
            len(extracted.pages),
            chunk_count,
            extracted.source_language,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("indexing failed for %s", doc_id_str)
        try:
            db.table("documents").update(
                {
                    "status": "failed",
                    "error_message": str(exc)[:500],
                    "processed_at": _now_iso(),
                }
            ).eq("id", doc_id_str).execute()
        except Exception:  # noqa: BLE001
            logger.exception("could not even mark doc=%s as failed", doc_id_str)
