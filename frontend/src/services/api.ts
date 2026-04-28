/**
 * HTTP client for the ARIA FastAPI backend.
 *
 * The frontend only talks to OUR backend — never to Groq/Gemini/etc. directly.
 * All third-party API keys live in HF Space secrets (build plan A2 §6).
 *
 * Day 1: only /health is wired. Real endpoints land per build plan A2 §28:
 *   POST /documents          (Day 4)
 *   POST /rag/ask  (SSE)     (Day 8)
 *   POST /translate          (Day 12)
 *   POST /tts                (Day 15–16)
 */

const API_BASE_URL: string =
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

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  env: string;
}

export function health(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}
