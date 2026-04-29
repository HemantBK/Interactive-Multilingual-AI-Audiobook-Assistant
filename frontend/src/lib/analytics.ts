/**
 * PostHog event tracking with consent gating (build plan §17 + §26
 * Day 22 / Day 25).
 *
 * Storage: PostHog uses localStorage (no cookies). Day 25 ConsentBanner
 * gates ALL track / identify calls behind explicit user opt-in stored
 * at `aria.analytics-consent`. No banner-decision yet ⇒ analytics off.
 *
 * Privacy:
 *   - autocapture off — only events we explicitly track
 *   - respect_dnt — Do-Not-Track honoured by the SDK itself
 *   - no PII in event properties (we send lengths, IDs, booleans)
 */

import posthog from 'posthog-js';

const apiKey = import.meta.env.VITE_POSTHOG_API_KEY as string | undefined;
const apiHost =
  (import.meta.env.VITE_POSTHOG_HOST as string | undefined) ?? 'https://us.i.posthog.com';

export const CONSENT_STORAGE_KEY = 'aria.analytics-consent';

let _initialised = false;

function _hasConsent(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(CONSENT_STORAGE_KEY) === 'granted';
  } catch {
    return false;
  }
}

export function initAnalytics(): boolean {
  if (_initialised) return true;
  if (!apiKey) return false;
  try {
    posthog.init(apiKey, {
      api_host: apiHost,
      autocapture: false,
      capture_pageview: false, // we'll start pageview only after consent
      persistence: 'localStorage',
      session_recording: { maskAllInputs: true },
      respect_dnt: true,
      opt_out_capturing_by_default: true,
    });
    _initialised = true;
    if (_hasConsent()) {
      posthog.opt_in_capturing();
      posthog.capture('$pageview');
    }
    return true;
  } catch (err) {
    console.warn('PostHog init failed — continuing without:', err);
    return false;
  }
}

/** Called by ConsentBanner when user grants consent. */
export function grantConsent(): void {
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, 'granted');
    } catch {
      /* private mode — best effort */
    }
  }
  if (_initialised) {
    try {
      posthog.opt_in_capturing();
      posthog.capture('$pageview');
    } catch {
      /* swallow */
    }
  }
}

/** Called by ConsentBanner when user declines. */
export function denyConsent(): void {
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, 'denied');
    } catch {
      /* swallow */
    }
  }
  if (_initialised) {
    try {
      posthog.opt_out_capturing();
      posthog.reset();
    } catch {
      /* swallow */
    }
  }
}

export function consentDecision(): 'granted' | 'denied' | 'pending' {
  if (typeof window === 'undefined') return 'pending';
  try {
    const v = window.localStorage.getItem(CONSENT_STORAGE_KEY);
    if (v === 'granted' || v === 'denied') return v;
    return 'pending';
  } catch {
    return 'pending';
  }
}

export function identify(userId: string): void {
  if (!_initialised || !_hasConsent()) return;
  try {
    posthog.identify(userId);
  } catch {
    /* swallow */
  }
}

export function reset(): void {
  if (!_initialised) return;
  try {
    posthog.reset();
  } catch {
    /* swallow */
  }
}

export function track(event: string, properties: Record<string, unknown> = {}): void {
  if (!_initialised || !_hasConsent()) return;
  try {
    posthog.capture(event, properties);
  } catch {
    /* swallow */
  }
}
