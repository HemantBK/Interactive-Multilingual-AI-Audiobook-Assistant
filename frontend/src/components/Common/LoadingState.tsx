import { useTranslation } from 'react-i18next';

interface Props {
  /** Override the default localised message. */
  message?: string;
  /** Compact variant for inline loading hints. */
  inline?: boolean;
}

/**
 * Reusable loading affordance with `role="status"` so screen readers
 * announce changes. Day 19 reusable wrapper — every fetch's loading state
 * goes through this so we can later swap in a skeleton without hunting.
 */
export function LoadingState({ message, inline = false }: Props) {
  const { t } = useTranslation();
  const text = message ?? t('loading.default');

  if (inline) {
    return (
      <span role="status" className="text-slate-500 text-sm">
        {text}
      </span>
    );
  }

  return (
    <div role="status" className="flex items-center gap-3 text-slate-500 p-4">
      <span aria-hidden className="block w-3 h-3 rounded-full bg-slate-300 animate-pulse" />
      <span className="text-sm">{text}</span>
    </div>
  );
}
