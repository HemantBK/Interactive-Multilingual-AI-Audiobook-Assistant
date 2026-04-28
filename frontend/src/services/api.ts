/**
 * HTTP client for the ARIA FastAPI backend.
 *
 * The frontend only talks to OUR backend — never to Groq/Gemini/etc. directly.
 * All third-party API keys live in HF Space secrets (build plan A2 §6).
 */

import type {
  CreateDocumentResponse,
  DocumentSummary,
  RAGEvent,
} from '../types';

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:7860';

export class ApiError extends Error {
  constructor(public status: number, public endpoint: string, message: string) {
    super(`${status} ${endpoint}: ${message}`);
    this.name = 'ApiError';
  }
}

export class BackendNotReadyError extends Error {
  constructor(endpoint: string, arrivingIn: string) {
    super(`${endpoint} is not implemented yet (arriving in ${arrivingIn}).`);
    this.name = 'BackendNotReadyError';
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
  return (await res.json()) as T;
}

async function authedRequest<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  return request<T>(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
  });
}

// ---------- /health ----------

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  env: string;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

// ---------- /auth ----------

export type AuthEventAction = 'login' | 'logout';

export async function notifyAuthEvent(
  action: AuthEventAction,
  accessToken: string,
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/${action}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });
    if (!res.ok) {
      console.warn(`auth ${action} audit returned ${res.status}`);
    }
  } catch (err) {
    console.warn(`auth ${action} audit failed`, err);
  }
}

// ---------- /documents ----------

export function listDocuments(accessToken: string): Promise<DocumentSummary[]> {
  return authedRequest<DocumentSummary[]>('/documents', accessToken);
}

export function getDocument(
  id: string,
  accessToken: string,
): Promise<DocumentSummary> {
  return authedRequest<DocumentSummary>(`/documents/${encodeURIComponent(id)}`, accessToken);
}

export async function createDocument(
  file: File,
  title: string,
  accessToken: string,
  idempotencyKey: string,
): Promise<CreateDocumentResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);

  const res = await fetch(`${API_BASE_URL}/documents`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Idempotency-Key': idempotencyKey,
    },
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, '/documents', body || res.statusText);
  }
  return (await res.json()) as CreateDocumentResponse;
}

// ---------- /rag/ask (SSE) ----------

export async function* streamRagAsk(
  documentId: string,
  question: string,
  accessToken: string,
  signal?: AbortSignal,
): AsyncGenerator<RAGEvent> {
  const res = await fetch(`${API_BASE_URL}/rag/ask`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ document_id: documentId, question }),
    signal,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, '/rag/ask', body || res.statusText);
  }
  if (!res.body) throw new Error('streamRagAsk: response body is null');

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += value;

      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith('data:')) continue;
        const json = line.slice('data:'.length).trim();
        if (!json) continue;
        try {
          yield JSON.parse(json) as RAGEvent;
        } catch (err) {
          console.warn('rag/ask: malformed SSE frame', json.slice(0, 120), err);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ---------- /translate ----------

export interface TranslateRequest {
  text: string;
  target_language: string;
  source_language?: string;
}

export interface TranslateResponse {
  translated_text: string;
  cached: boolean;
  source_language: string | null;
  target_language: string;
}

export function translate(
  body: TranslateRequest,
  accessToken: string,
): Promise<TranslateResponse> {
  return authedRequest<TranslateResponse>('/translate', accessToken, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ---------- /tts + /voices ----------

export interface TTSRequest {
  text: string;
  voice_id: string;
}

export interface TTSResponse {
  audio_url: string;
  mime_type: string;
  voice_id: string;
  language: string;
  cached: boolean;
  size_bytes: number | null;
  fallback_used: boolean;
}

export interface VoiceOptionDTO {
  voice_id: string;
  language: string;
  label: string;
  gender: 'female' | 'male';
}

export function synthesizeTTS(
  body: TTSRequest,
  accessToken: string,
): Promise<TTSResponse> {
  return authedRequest<TTSResponse>('/tts', accessToken, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function listVoices(accessToken: string): Promise<VoiceOptionDTO[]> {
  return authedRequest<VoiceOptionDTO[]>('/voices', accessToken);
}
