/**
 * Domain types shared across the frontend. Mirrors the backend data model
 * in infra/supabase/migrations/0001_initial_schema.sql — keep them aligned.
 *
 * Day 1: only the types needed by the auth + landing scaffold. Document /
 * RAG / chat types land alongside the endpoints that produce them
 * (Week 1 Day 4+, see build plan A2.md).
 */

export type DocumentStatus =
  | 'queued'
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'failed';

export type SourceType = 'pdf' | 'image' | 'text';
