/**
 * HTTP client for the ARIA FastAPI backend.
 *
 * This is the ONLY place the frontend talks to AI services. There are no
 * direct third-party API calls from the browser. All secrets live in the
 * backend environment (Hugging Face Space secrets in production).
 *
 * The function signatures below mirror what App.tsx already consumes so the
 * UI keeps compiling. Real bodies are filled in as backend endpoints land:
 *   - extractTextFromDocument  → Week 1 Day 4–7   (POST /documents)
 *   - generateEmbeddings       → Week 1 Day 6     (server-side during upload)
 *   - answerQuestionWithRAG    → Week 2 Day 8–9   (POST /rag/ask, SSE)
 *   - translateText            → Week 2 Day 12    (POST /translate)
 *   - generateSpeech           → Week 3 Day 15–16 (POST /tts)
 *   - transcribeAudio          → deferred to v2   (voice input dropped for v1)
 */

import type { DocumentChunk, Language } from '../types';

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:7860';

// ---------------------------------------------------------------------------
// Low-level fetch helper
// ---------------------------------------------------------------------------

export class BackendNotReadyError extends Error {
  constructor(endpoint: string, arrivingIn: string) {
    super(`Backend endpoint ${endpoint} is not implemented yet (arriving in ${arrivingIn}).`);
    this.name = 'BackendNotReadyError';
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public endpoint: string,
    message: string,
  ) {
    super(`${status} ${endpoint}: ${message}`);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, path, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Real endpoint: /health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  env: string;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

// ---------------------------------------------------------------------------
// Stubs — signatures preserved for App.tsx. Filled in as endpoints ship.
// ---------------------------------------------------------------------------

export async function extractTextFromDocument(
  _base64Data: string | null,
  _mimeType: string,
  _forceOcr: boolean = false,
  _targetLanguage?: Language,
  _url?: string,
): Promise<{ displayedText: string; ragText: string }> {
  throw new BackendNotReadyError('POST /documents', 'Week 1 Day 4–7');
}

export async function translateText(_text: string, _targetLanguage: Language): Promise<string> {
  throw new BackendNotReadyError('POST /translate', 'Week 2 Day 12');
}

export async function generateSpeech(_text: string, _voiceName: string): Promise<Uint8Array> {
  throw new BackendNotReadyError('POST /tts', 'Week 3 Day 15–16');
}

export async function transcribeAudio(_base64Audio: string, _mimeType: string): Promise<string> {
  throw new BackendNotReadyError(
    'POST /transcribe',
    'v2 (voice input was dropped from v1 scope)',
  );
}

export async function generateEmbeddings(_chunks: string[]): Promise<DocumentChunk[]> {
  throw new BackendNotReadyError(
    'server-side embedding during upload',
    'Week 1 Day 6 (no direct frontend call — runs on /documents)',
  );
}

export async function answerQuestionWithRAG(
  _question: string,
  _contextChunks: DocumentChunk[],
): Promise<string> {
  throw new BackendNotReadyError('POST /rag/ask', 'Week 2 Day 8–9');
}
