/**
 * Sentry init for the SPA (build plan §17 Day 22).
 *
 * Sampling: traces 10%, errors 100%. Replays disabled — they're a separate
 * Sentry product with its own quota and we don't need them at v1.
 *
 * Privacy: sendDefaultPii=false. We don't capture URLs of signed Storage
 * URLs (which contain doc IDs) or auth tokens. Day 26 security review
 * decides whether to add hashed user_id via Sentry.setUser().
 *
 * No-op if VITE_SENTRY_DSN_FRONTEND is unset (local dev / unconfigured).
 */

import * as Sentry from '@sentry/react';

const dsn = import.meta.env.VITE_SENTRY_DSN_FRONTEND as string | undefined;
const env = (import.meta.env.MODE as string | undefined) ?? 'development';

let _initialised = false;

export function initSentry(): boolean {
  if (_initialised) return true;
  if (!dsn) return false;
  try {
    Sentry.init({
      dsn,
      environment: env,
      tracesSampleRate: 0.1,
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 0,
      sendDefaultPii: false,
      // Filter out signed-URL query strings (doc IDs leak in them).
      beforeBreadcrumb(breadcrumb) {
        if (breadcrumb.data?.url && typeof breadcrumb.data.url === 'string') {
          try {
            const u = new URL(breadcrumb.data.url);
            // Drop search params that contain bearer-like tokens or signatures
            for (const k of ['token', 'sig', 'X-Amz-Signature']) {
              u.searchParams.delete(k);
            }
            breadcrumb.data.url = u.toString();
          } catch {
            // Invalid URL — leave alone
          }
        }
        return breadcrumb;
      },
    });
    _initialised = true;
    return true;
  } catch (err) {
    console.warn('Sentry init failed — continuing without:', err);
    return false;
  }
}

export function captureException(error: unknown, context?: Record<string, unknown>): void {
  if (!_initialised) return;
  try {
    Sentry.captureException(error, context ? { extra: context } : undefined);
  } catch {
    // Swallow — observability errors must never break the app.
  }
}
