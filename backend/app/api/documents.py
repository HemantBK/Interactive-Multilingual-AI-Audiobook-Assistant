"""POST /documents (upload), GET /documents (list), GET /documents/{id} (one)."""

# NOTE: do NOT add `from __future__ import annotations` here.
# FastAPI introspects `BackgroundTasks` via pydantic's TypeAdapter, which
# can't resolve forward refs to special FastAPI types. PEP 563 stringified
# annotations break the @router.post decorator at import time with
# `PydanticUndefinedAnnotation: name 'BackgroundTasks' is not defined`.

import hashlib
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.core.limiter import limiter
from app.core.security import AuthenticatedUser, current_user
from app.db.supabase import user_client
from app.models.schemas import CreateDocumentResponse, DocumentSummary
from app.services import idempotency, quotas
from app.services.audit import write_audit
from app.services.pipeline import run_indexing
from app.services.uploads import (
    UploadValidationError,
    assert_size,
    detect_source_type,
    strip_exif,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_ENDPOINT = "/documents"
_LIST_DEFAULT_LIMIT = 100

_DOC_NAMESPACE = uuid.UUID("9b7e8c70-2d4a-4f4e-9e2a-aa00ddee1100")


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post(
    "",
    response_model=CreateDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def create_document(
    request: Request,
    background: BackgroundTasks,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form(min_length=1, max_length=500)],
) -> CreateDocumentResponse:
    """
    Upload a document. Required header: `Idempotency-Key: <uuid>`.

    Validation chain: size → MIME → magic bytes → (image only) EXIF strip →
    daily-uploads quota check → row insert → background indexing.

    Day 18 adds slowapi 5/min/IP throttling and a per-user daily uploads
    cap (default 10/day, see RATE_LIMIT_DAILY_UPLOADS).
    """
    contents = await file.read()

    try:
        assert_size(contents)
        source_type, real_mime, ext = detect_source_type(contents, file.content_type)
        if source_type == "image":
            contents = strip_exif(contents, real_mime)
    except UploadValidationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    request_hash = hashlib.sha256(
        contents + b"\x00" + title.encode("utf-8") + b"\x00" + user.user_id.encode("ascii")
    ).hexdigest()

    db = user_client(user.access_token)

    # Idempotent replay — return cached response without burning quota.
    cached = idempotency.lookup(
        client=db, key=idempotency_key, user_id=user.user_id, endpoint=_ENDPOINT
    )
    if cached is not None:
        if cached["request_hash"] != request_hash:
            raise idempotency.IdempotencyConflictError()
        return CreateDocumentResponse(**cached["response"])

    # Quota check (only for fresh uploads — replays already counted).
    quotas.assert_under_cap(
        db, user_id=user.user_id, counter="documents_uploaded", delta=1
    )

    doc_id = uuid.uuid5(_DOC_NAMESPACE, f"{user.user_id}|{idempotency_key}")
    storage_path = f"{user.user_id}/{doc_id}/original.{ext}"

    db.storage.from_("documents").upload(
        path=storage_path,
        file=contents,
        file_options={"content-type": real_mime, "upsert": "true"},
    )

    upserted = (
        db.table("documents")
        .upsert(
            {
                "id": str(doc_id),
                "user_id": user.user_id,
                "title": title,
                "source_type": source_type,
                "storage_path": storage_path,
                "status": "queued",
            },
            on_conflict="id",
        )
        .execute()
    )
    if not upserted.data:
        raise HTTPException(500, "Document upsert failed")

    row = upserted.data[0]
    response = CreateDocumentResponse(
        document_id=row["id"],
        status=row["status"],
        title=row["title"],
        source_type=row["source_type"],
        page_count=row.get("page_count"),
        created_at=row["created_at"],
    )

    idempotency.store(
        client=db,
        key=idempotency_key,
        user_id=user.user_id,
        endpoint=_ENDPOINT,
        request_hash=request_hash,
        response=response.model_dump(),
        status_code=201,
    )

    quotas.bump(db, user_id=user.user_id, counter="documents_uploaded", delta=1)

    write_audit(
        action="document.upload",
        user_id=user.user_id,
        resource_type="document",
        resource_id=str(doc_id),
        ip=_client_ip(request),
        metadata={"source_type": source_type, "size_bytes": len(contents)},
    )

    background.add_task(run_indexing, doc_id, user.access_token)

    return response


@router.get("", response_model=list[DocumentSummary])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> list[DocumentSummary]:
    """List the caller's documents, newest first. RLS scopes the query to user_id."""
    db = user_client(user.access_token)
    result = (
        db.table("documents")
        .select("*")
        .eq("user_id", user.user_id)
        .order("created_at", desc=True)
        .limit(_LIST_DEFAULT_LIMIT)
        .execute()
    )
    return [DocumentSummary(**row) for row in (result.data or [])]


@router.get("/{document_id}", response_model=DocumentSummary)
@limiter.limit("60/minute")
async def get_document(
    request: Request,
    document_id: str,
    user: Annotated[AuthenticatedUser, Depends(current_user)],
) -> DocumentSummary:
    """Fetch one document the caller owns. 404 if absent or not theirs (RLS)."""
    db = user_client(user.access_token)
    result = (
        db.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user.user_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return DocumentSummary(**result.data[0])
