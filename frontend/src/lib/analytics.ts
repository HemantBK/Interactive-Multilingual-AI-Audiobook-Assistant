/**
 * PostHog event tracking (build plan A2 §17, Day 22).
 *
 * Event naming:  <surface>.<verb>          e.g. "document.uploaded"
 * Properties:    no raw user content. Use lengths, types, IDs, booleans.
 *
 * No-op if VITE_POSTHOG_API_KEY is unset. All calls are best-effort —
 * analytics failures must never surface to the user.
 */

import posthog from 'posthog-js';

const apiKey = import.meta.env.VITE_POSTHOG_API_KEY as string | undefined;
const apiHost =
  (import.meta.env.VITE_POSTHOG_HOST as string | undefined) ??
  'https://us.i.posthog.com';

let _initialised = false;

export function initAnalytics(): boolean {
  if (_initialised) return true;
  if (!apiKey) return false;
  try {
    posthog.init(apiKey, {
      api_host: apiHost,
      autocapture: false,         // we explicitly track named events
      capture_pageview: true,
      persistence: 'localStorage',
      // Privacy defaults — no session recording, no auto-PII.
      session_recording: { maskAllInputs: true },
      respect_dnt: true,
    });
    _initialised = true;
    return true;
  } catch (err) {
    console.warn('PostHog init failed — continuing without:', err);
    return false;
  }
}

/**
 * Tag the current session with a stable user identifier. Day 22 caller is
 * useAuth on SIGNED_IN. We pass Supabase's user_id (UUID) — already
 * non-PII (not an email).
 */
export function identify(userId: string): void {
  if (!_initialised) return;
  try {
    posthog.identify(userId);
  } catch {
    // Swallow — analytics failures don't break the app.
  }
}

export function reset(): void {
  if (!_initialised) return;
  try {
    posthog.reset();
  } catch {
    // Swallow.
  }
}

export function track(
  event: string,
  properties: Record<string, unknown> = {},
): void {
  if (!_initialised) return;
  try {
    posthog.capture(event, properties);
  } catch {
    // Swallow.
  }
}
