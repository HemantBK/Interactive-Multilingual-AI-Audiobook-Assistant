import { useTranslation } from 'react-i18next';

import { VOICE_OPTIONS } from './voices';

interface Props {
  /** Current voice_id — controls the select. */
  value: string;
  /** Two-letter ISO code; filters which voices are shown. */
  language: string | null;
  onChange: (voiceId: string) => void;
  disabled?: boolean;
}

/**
 * Per-message voice override. Filters to the doc's language by default,
 * falling back to English when the language isn't in our catalog.
 */
export function VoicePicker({ value, language, onChange, disabled }: Props) {
  const { t } = useTranslation();
  const lang = language && VOICE_OPTIONS.some((v) => v.language === language) ? language : 'en';
  const options = VOICE_OPTIONS.filter((v) => v.language === lang);

  return (
    <label className="flex items-center gap-2">
      <span className="sr-only">{t('audio.voiceLabel')}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-label={t('audio.voiceLabel')}
        className="text-xs border border-slate-300 rounded px-2 py-1 bg-white disabled:bg-slate-50"
      >
        {options.map((v) => (
          <option key={v.voice_id} value={v.voice_id}>
            {v.label}
          </option>
        ))}
      </select>
    </label>
  );
}
