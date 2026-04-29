import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { consentDecision, denyConsent, grantConsent } from '../../lib/analytics';

/**
 * One-time analytics consent banner (build plan §26 Day 25).
 *
 * Shows on first visit while `aria.analytics-consent` localStorage key
 * is unset. Choice persists; banner does not reappear unless the user
 * clears site data.
 *
 * "Decline" is a real first-class option — the SDK is initialised with
 * `opt_out_capturing_by_default: true`, so declining is the no-op path
 * and granting calls `posthog.opt_in_capturing()`.
 */
export function ConsentBanner() {
  const { t } = useTranslation();
  const [decided, setDecided] = useState<boolean>(true); // optimistic — assume decided until mount

  useEffect(() => {
    setDecided(consentDecision() !== 'pending');
  }, []);

  if (decided) return null;

  function handleGrant() {
    grantConsent();
    setDecided(true);
  }

  function handleDeny() {
    denyConsent();
    setDecided(true);
  }

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label={t('consent.regionLabel')}
      className="fixed inset-x-2 bottom-2 z-40 mx-auto max-w-3xl rounded border border-slate-300 bg-white shadow-md p-3 flex flex-col gap-2 sm:flex-row sm:items-center"
    >
      <p className="text-sm text-slate-700 flex-1">{t('consent.message')}</p>
      <div className="flex gap-2 shrink-0">
        <button
          type="button"
          onClick={handleDeny}
          className="text-xs border border-slate-300 rounded px-3 py-1 bg-white"
        >
          {t('consent.decline')}
        </button>
        <button
          type="button"
          onClick={handleGrant}
          className="text-xs rounded px-3 py-1 bg-slate-900 text-white"
        >
          {t('consent.accept')}
        </button>
      </div>
    </div>
  );
}
