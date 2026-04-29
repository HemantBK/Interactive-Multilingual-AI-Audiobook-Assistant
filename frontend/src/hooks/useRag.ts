/**
 * RAG state machine + SSE consumer (build plan §12 + Day 10).
 *
 *  idle        ← initial / after reset
 *    │  ask()
 *    ▼
 *  asking      ← request issued, waiting for first event
 *    │  RAGEvent {event: "start"}
 *    ▼
 *  streaming   ← assistant message exists, waiting for answer / error
 *    │  {event: "answer"} → message.text + citations populated
 *    │  {event: "done"}   → message.status = 'done', latency captured
 *    │  {event: "error"}  → message.status = 'error', message.error captured
 *    ▼
 *  done | error
 *    │  ask()
 *    ▼
 *  asking (cycle repeats)
 *
 * In-flight requests are aborted when the caller asks a new question or
 * unmounts the component. Each ask() starts a fresh AbortController.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { track } from '../lib/analytics';
import { ApiError, streamRagAsk } from '../services/api';
import type { AssistantMessage, ChatMessage, Citation, ChunkRef } from '../types';

export type RagPhase = 'idle' | 'asking' | 'streaming' | 'done' | 'error';

export interface UseRagResult {
  phase: RagPhase;
  messages: ChatMessage[];
  ask: (documentId: string, question: string) => Promise<void>;
  reset: () => void;
}

function newId(): string {
  return crypto.randomUUID();
}

export function useRag(accessToken: string | null): UseRagResult {
  const [phase, setPhase] = useState<RagPhase>('idle');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  // Always abort an in-flight stream on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  const updateAssistant = useCallback((id: string, patch: Partial<AssistantMessage>) => {
    setMessages((prev) =>
      prev.map((m) => (m.role === 'assistant' && m.id === id ? { ...m, ...patch } : m)),
    );
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setPhase('idle');
  }, []);

  const ask = useCallback(
    async (documentId: string, question: string) => {
      if (!accessToken) return;
      const trimmed = question.trim();
      if (!trimmed) return;

      // Cancel any prior in-flight request.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userId = newId();
      const assistantId = newId();
      const t0 = Date.now();

      setMessages((prev) => [
        ...prev,
        {
          id: userId,
          role: 'user',
          text: trimmed,
          createdAt: t0,
        },
        {
          id: assistantId,
          role: 'assistant',
          status: 'streaming',
          text: '',
          citations: [],
          retrievedChunks: [],
          latencyMs: null,
          error: null,
          createdAt: t0,
        },
      ]);
      setPhase('asking');
      track('rag.asked', {
        question_chars: trimmed.length,
        document_id: documentId,
      });

      try {
        for await (const ev of streamRagAsk(documentId, trimmed, accessToken, controller.signal)) {
          if (ev.event === 'start') {
            setPhase('streaming');
          } else if (ev.event === 'answer') {
            updateAssistant(assistantId, {
              text: ev.answer,
              citations: ev.citations as Citation[],
            });
          } else if (ev.event === 'done') {
            updateAssistant(assistantId, {
              status: 'done',
              retrievedChunks: ev.retrieved_chunks as ChunkRef[],
              latencyMs: ev.latency_ms,
            });
            setPhase('done');
            track('rag.answered', {
              latency_ms: ev.latency_ms,
              chunk_count: ev.retrieved_chunks?.length ?? 0,
            });
          } else if (ev.event === 'error') {
            updateAssistant(assistantId, {
              status: 'error',
              error: ev.error,
            });
            setPhase('error');
            track('rag.errored', { error_short: ev.error.slice(0, 80) });
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg =
          err instanceof ApiError
            ? `${err.status} — ${err.message}`
            : err instanceof Error
              ? err.message
              : String(err);
        updateAssistant(assistantId, { status: 'error', error: msg });
        setPhase('error');
      }
    },
    [accessToken, updateAssistant],
  );

  return { phase, messages, ask, reset };
}
