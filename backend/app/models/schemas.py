"""
Pydantic request/response schemas.

Days 4–7: document upload + summary + list.
Day 8: RAG request + Citation. SSE event payloads stay loosely typed (dicts).
Day 12: TranslateRequest / TranslateResponse.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["pdf", "image", "text"]
DocumentStatus = Literal["queued", "uploading", "processing", "ready", "failed"]


class CreateDocumentResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    title: str
    source_type: SourceType
    page_count: int | None = None
    created_at: str


class DocumentSummary(BaseModel):
    id: str
    user_id: str
    title: str
    source_type: SourceType
    status: DocumentStatus
    page_count: int | None = None
    source_language: str | None = None
    error_message: str | None = None
    created_at: str
    processed_at: str | None = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable error message")
    code: str | None = Field(None, description="Stable, machine-readable error code")


# ---------- RAG ----------


class Citation(BaseModel):
    chunk_id: int
    quote: str


class RAGRequest(BaseModel):
    document_id: str = Field(..., min_length=36, max_length=36)
    question: str = Field(..., min_length=1, max_length=2000)


# ---------- Translate ----------


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    target_language: str = Field(..., min_length=2, max_length=5)
    source_language: str | None = Field(default=None, min_length=2, max_length=5)


class TranslateResponse(BaseModel):
    translated_text: str
    cached: bool
    source_language: str | None
    target_language: str


# ---------- TTS ----------


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voice_id: str = Field(..., min_length=2, max_length=40)


class TTSResponse(BaseModel):
    audio_url: str
    mime_type: str
    voice_id: str
    language: str
    cached: bool
    size_bytes: int | None = None
    fallback_used: bool = False


class VoiceOption(BaseModel):
    voice_id: str
    language: str
    label: str
    gender: Literal["female", "male"]
