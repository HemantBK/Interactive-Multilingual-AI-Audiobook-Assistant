"""
RAG pipeline orchestrator.

Day 8: embed → top-20 → load chunks → rerank → top-5 → Groq stream → emit.
Day 9: + citation validation, conversations row, latency + token tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from supabase import Client

from app.services import storage
from app.services.citations import validate_citations
from app.services.conversations import persist_conversation
from app.services.embedding import embed_texts
from app.services.groq_client import (
    DEFAULT_MODEL,
    GroqUnavailableError,
    groq_stream_chat,
)
from app.services.output_filter import filter_answer
from app.services.prompts import build_rag_prompt
from app.services.rerank import rerank
from app.services.retrieval import retrieve_top_k

logger = logging.getLogger(__name__)

TOP_K_RETRIEVE = 20
TOP_K_RERANK = 5


def _ms_since(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


async def stream_rag_answer(
    db: Client,
    user_id: str,
    document_id: str,
    question: str,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yield SSE-friendly events:
      {"event": "start"}
      {"event": "answer", "answer": str, "citations": [{chunk_id, quote}]}
      {"event": "done",   "retrieved_chunks": [...], "latency_ms": int}
      {"event": "error",  "error": str}

    Day 9: every successful run writes a row to public.conversations with
    cited_chunk_ids, latency_ms, tokens_in, tokens_out, model.
    """
    yield {"event": "start"}

    started = time.monotonic()
    [question_embedding] = await asyncio.to_thread(embed_texts, [question])

    top20 = await asyncio.to_thread(
        retrieve_top_k, db, document_id, question_embedding, k=TOP_K_RETRIEVE
    )
    if not top20:
        yield {"event": "answer", "answer": "", "citations": []}
        yield {
            "event": "done",
            "retrieved_chunks": [],
            "latency_ms": _ms_since(started),
        }
        return

    text_path = top20[0]["text_storage_path"]
    try:
        chunks_blob = await asyncio.to_thread(
            storage.download, db, storage.BUCKET_CHUNKS, text_path
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("could not load chunks blob for doc=%s", document_id)
        yield {"event": "error", "error": f"chunk text fetch failed: {exc}"}
        return

    try:
        chunks_data = json.loads(chunks_blob.decode("utf-8"))
        text_by_index = {c["chunk_index"]: c["text"] for c in chunks_data}
    except (json.JSONDecodeError, KeyError) as exc:
        logger.exception("malformed chunks blob for doc=%s", document_id)
        yield {"event": "error", "error": f"corrupt chunks blob: {exc}"}
        return

    for c in top20:
        c["text"] = text_by_index.get(c["chunk_index"], "")

    top5 = await asyncio.to_thread(rerank, question, top20, k=TOP_K_RERANK)

    messages = build_rag_prompt(question, top5)

    parts: list[str] = []
    usage: dict[str, int] = {}

    try:
        async for token in groq_stream_chat(
            messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            capture_usage=usage,
        ):
            parts.append(token)
    except GroqUnavailableError as exc:
        yield {"event": "error", "error": f"LLM unavailable: {exc}"}
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Groq streaming failed")
        yield {"event": "error", "error": str(exc)[:200]}
        return

    raw = "".join(parts).strip()
    answer: str
    raw_citations: list[Any]
    try:
        parsed = json.loads(raw)
        answer = str(parsed.get("answer", ""))
        cit_field = parsed.get("citations")
        raw_citations = list(cit_field) if isinstance(cit_field, list) else []
    except json.JSONDecodeError:
        logger.warning("RAG output not valid JSON: %r", raw[:200])
        answer = raw
        raw_citations = []

    valid_citations, dropped = validate_citations(raw_citations, top5)
    if dropped:
        logger.info(
            "rag.ask dropped %d citations (doc=%s) — first reasons: %s",
            len(dropped),
            document_id,
            [d.get("reason") for d in dropped[:5]],
        )

    # Day 13: scan model output for credential / script / data-URL exfil.
    # HARD findings replace the answer with a safe rejection; SOFT findings
    # (unknown URLs) are logged but the answer passes through.
    answer, output_findings = filter_answer(answer)
    if output_findings:
        logger.warning(
            "rag.ask output_filter findings (doc=%s): %s",
            document_id,
            output_findings,
        )

    latency_ms = _ms_since(started)
    cited_chunk_ids = [c["chunk_id"] for c in valid_citations]

    await asyncio.to_thread(
        persist_conversation,
        db,
        user_id=user_id,
        document_id=document_id,
        question=question,
        answer=answer,
        cited_chunk_ids=cited_chunk_ids,
        latency_ms=latency_ms,
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
        model=DEFAULT_MODEL,
    )

    yield {"event": "answer", "answer": answer, "citations": valid_citations}
    yield {
        "event": "done",
        "retrieved_chunks": [
            {
                "id": c["id"],
                "chunk_index": c["chunk_index"],
                "page_number": c["page_number"],
                "bbox": c.get("bbox"),
                "score": c.get("score", 0.0),
            }
            for c in top5
        ],
        "latency_ms": latency_ms,
    }
