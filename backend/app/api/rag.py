"""POST /rag/ask — SSE-streamed Q&A over the user's documents."""

# NOTE: do NOT add `from __future__ import annotations` here.
# FastAPI's StreamingResponse return type is introspected via pydantic's
# TypeAdapter, which can't resolve PEP 563 stringified forward refs to
# special FastAPI types — would raise PydanticUndefinedAnnotation at
# import time.

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.limiter import limiter
from app.core.security import AuthenticatedUser, current_user
from app.db.supabase import user_client
from app.models.schemas import RAGRequest
from app.services import quotas
from app.services.audit import write_audit
from app.services.rag import stream_rag_answer

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask")
@limiter.limit("20/minute")
async def rag_ask(
    request: Request,
    body: RAGRequest,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> StreamingResponse:
    """
    Answer a question against a single document. Returns Server-Sent Events.

    Day 18: 20/min/IP slowapi limit + per-user daily rag_queries cap
    (RATE_LIMIT_DAILY_QUERIES, default 500). Quota debited only after
    auth + doc-readiness checks pass — failed requests don't burn quota.
    """
    db = user_client(user.access_token)

    doc_check = (
        db.table("documents")
        .select("status")
        .eq("id", body.document_id)
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    )
    if not doc_check.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    doc_status = doc_check.data[0]["status"]
    if doc_status != "ready":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Document is {doc_status!r}, not ready for queries yet",
        )

    quotas.assert_under_cap(
        db, user_id=user.user_id, counter="rag_queries", delta=1
    )

    write_audit(
        action="rag.ask",
        user_id=user.user_id,
        resource_type="document",
        resource_id=body.document_id,
        metadata={"q_len": len(body.question)},
    )

    quotas.bump(db, user_id=user.user_id, counter="rag_queries", delta=1)

    async def event_stream():
        async for event in stream_rag_answer(
            db, user.user_id, body.document_id, body.question
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
