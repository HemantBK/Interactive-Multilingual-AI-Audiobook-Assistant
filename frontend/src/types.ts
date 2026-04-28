/**
 * Domain types shared across the frontend. Mirrors the backend data model
 * in infra/supabase/migrations/0001_initial_schema.sql — keep them aligned.
 */

export type DocumentStatus =
  | 'queued'
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'failed';

export type SourceType = 'pdf' | 'image' | 'text';

export interface DocumentSummary {
  id: string;
  user_id: string;
  title: string;
  source_type: SourceType;
  status: DocumentStatus;
  page_count: number | null;
  source_language: string | null;
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface CreateDocumentResponse {
  document_id: string;
  status: DocumentStatus;
  title: string;
  source_type: SourceType;
  page_count: number | null;
  created_at: string;
}

// ---------- RAG ----------

export interface BBox {
  /** 1-indexed page number (PDFs may have many; images always 1). */
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface Citation {
  chunk_id: number;
  quote: string;
}

export interface ChunkRef {
  id: number;
  chunk_index: number;
  page_number: number;
  /** Word-level boxes for the chunk. PDFs use point coords, images use pixels. */
  bbox: BBox[] | null;
  score: number;
}

export type RAGEvent =
  | { event: 'start' }
  | { event: 'answer'; answer: string; citations: Citation[] }
  | { event: 'done'; retrieved_chunks: ChunkRef[]; latency_ms: number }
  | { event: 'error'; error: string };

// ---------- Chat (frontend-only) ----------

export interface UserMessage {
  id: string;
  role: 'user';
  text: string;
  createdAt: number;
}

export type AssistantStatus = 'streaming' | 'done' | 'error';

export interface AssistantMessage {
  id: string;
  role: 'assistant';
  status: AssistantStatus;
  text: string;
  citations: Citation[];
  retrievedChunks: ChunkRef[];
  latencyMs: number | null;
  error: string | null;
  createdAt: number;
}

export type ChatMessage = UserMessage | AssistantMessage;

// ---------- Citation jump (App-level shared state) ----------

export interface CitationJump {
  citation: Citation;
  chunk: ChunkRef | undefined;
  /** Stamps to force re-fire if the same citation is clicked twice. */
  nonce: number;
}
