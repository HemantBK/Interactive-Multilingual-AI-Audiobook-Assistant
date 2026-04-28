/**
 * Fetch + poll the caller's documents.
 *
 * Polls every 5 s while authenticated. Cleaner than Supabase Realtime for v1
 * (no second subscription channel; also keeps the door open to backend-side
 * derived fields like cost_usd_estimate that live outside the documents table).
 *
 * Polling pauses if the user signs out; resumes on sign-in.
 */

import { useCallback, useEffect, useState } from 'react';

import { listDocuments } from '../services/api';
import type { DocumentSummary } from '../types';

const POLL_INTERVAL_MS = 5_000;

export interface UseDocumentsResult {
  documents: DocumentSummary[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDocuments(accessToken: string | null): UseDocumentsResult {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOnce = useCallback(async () => {
    if (!accessToken) return;
    try {
      const list = await listDocuments(accessToken);
      setDocuments(list);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) {
      setDocuments([]);
      setLoading(false);
      return;
    }

    let alive = true;
    void fetchOnce();
    const id = setInterval(() => {
      if (alive) void fetchOnce();
    }, POLL_INTERVAL_MS);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [accessToken, fetchOnce]);

  return { documents, loading, error, refresh: fetchOnce };
}
