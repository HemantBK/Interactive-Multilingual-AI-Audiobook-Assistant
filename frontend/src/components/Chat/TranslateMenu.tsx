import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { track } from '../../lib/analytics';
import { ApiError, translate } from '../../services/api';

/**
 * 14 target languages per build plan §1. Labels are in the target's own
 * script — translating the language name itself wastes lookup time and
 * "हिन्दी" / "Tamil" / "中文" are universally legible to native readers.
 */
export const TRANSLATION_TARGETS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'bn', label: 'বাংলা' },
  { code: 'mr', label: 'मराठी' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'ja', label: '日本語' },
  { code: 'zh', label: '中文' },
  { code: 'pt', label: 'Português' },
  { code: 'it', label: 'Italiano' },
  { code: 'ru', label: 'Русский' },
] as const;

export interface TranslationView {
  langCode: string;
  langLabel: string;
  text: string;
  cached: boolean;
}

interface Props {
  sourceText: string;
  sourceLanguageHint?: string | null;
  accessToken: string | null;
  current: TranslationView | null;
  onChange: (view: TranslationView | null) => void;
}

export function TranslateMenu({
  sourceText,
  sourceLanguageHint,
  accessToken,
  current,
  onChange,
}: Props) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSelect(code: string) {
    if (!code || !accessToken) return;
    if (current && current.langCode === code) return;
    setBusy(true);
    setError(null);
    try {
      const res = await translate(
        {
          text: sourceText,
          target_language: code,
          source_language: sourceLanguageHint ?? undefined,
        },
        accessToken,
      );
      const target = TRANSLATION_TARGETS.find((l) => l.code === code);
      onChange({
        langCode: code,
        langLabel: target?.label ?? code,
        text: res.translated_text,
        cached: res.cached,
      });
      track('translate.requested', {
        target_language: code,
        cached: res.cached,
        chars: sourceText.length,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `${err.status} — ${err.message}`
          : err instanceof Error
            ? err.message
            : String(err);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2 mt-2">
      <label className="text-[11px] text-slate-500">
        <span className="sr-only">{t('chat.translate.label')}</span>
        <select
          value={current?.langCode ?? ''}
          onChange={(e) => void handleSelect(e.target.value)}
          disabled={busy || !accessToken}
          className="text-xs border border-slate-300 rounded px-2 py-1 bg-white disabled:bg-slate-50"
          aria-label={t('chat.translate.label')}
        >
          <option value="">{t('chat.translate.placeholder')}</option>
          {TRANSLATION_TARGETS.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </label>
      {busy && (
        <span role="status" className="text-[11px] text-slate-500">
          {t('chat.translate.busy')}
        </span>
      )}
      {current && !busy && (
        <button
          type="button"
          onClick={() => onChange(null)}
          className="text-[11px] text-slate-600 underline"
        >
          {t('chat.translate.clear')}
        </button>
      )}
      {error && (
        <span role="alert" className="text-[11px] text-red-700">
          {error}
        </span>
      )}
    </div>
  );
}
