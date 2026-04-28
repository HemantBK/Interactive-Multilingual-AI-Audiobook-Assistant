/**
 * Resolve a Supabase Storage path to a short-lived signed URL the browser
 * can fetch directly. RLS on the `documents` bucket only lets the file's
 * owner generate a signed URL — Supabase verifies via the user JWT.
 *
 * Returns { url, loading, error }. URL is null until resolved.
 *
 * Day 11 uses this for the PDF / image viewer source. Audio (Day 16) and
 * chunk-text (deferred) reuse the same pattern via different buckets.
 */

import { useEffect, useState } from 'react';

import { supabase } from '../lib/supabase';

const BUCKET_DOCUMENTS = 'documents';
const SIGNED_URL_TTL_SECONDS = 60 * 30; // 30 min

export interface UseDocumentSourceResult {
  url: string | null;
  loading: boolean;
  error: string | null;
}

export function useDocumentSource(
  storagePath: string | null,
): UseDocumentSourceResult {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(storagePath != null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!storagePath) {
      setUrl(null);
      setLoading(false);
      setError(null);
      return;
    }

    let alive = true;
    setLoading(true);
    setError(null);

    void (async () => {
      const { data, error: err } = await supabase.storage
        .from(BUCKET_DOCUMENTS)
        .createSignedUrl(storagePath, SIGNED_URL_TTL_SECONDS);

      if (!alive) return;
      if (err) {
        setError(err.message);
        setUrl(null);
      } else {
        setUrl(data?.signedUrl ?? null);
      }
      setLoading(false);
    })();

    return () => {
      alive = false;
    };
  }, [storagePath]);

  return { url, loading, error };
}
