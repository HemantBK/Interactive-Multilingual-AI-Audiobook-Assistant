import { useTranslation } from 'react-i18next';

import type { DocumentStatus, DocumentSummary } from '../../types';

const STATUS_CLASS: Record<DocumentStatus, string> = {
  queued: 'bg-slate-200 text-slate-800',
  uploading: 'bg-slate-200 text-slate-800',
  processing: 'bg-amber-100 text-amber-900',
  ready: 'bg-green-100 text-green-900',
  failed: 'bg-red-100 text-red-900',
};

interface Props {
  documents: DocumentSummary[];
  loading: boolean;
  error: string | null;
  selectedId?: string | null;
  onSelect?: (doc: DocumentSummary) => void;
}

export function DocumentList({ documents, loading, error, selectedId, onSelect }: Props) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <p role="status" className="text-slate-500">
        …
      </p>
    );
  }
  if (error) {
    return (
      <p role="alert" className="text-red-700 text-sm">
        {error}
      </p>
    );
  }
  if (documents.length === 0) {
    return <p className="text-slate-500">{t('documents.empty')}</p>;
  }

  return (
    <ul className="divide-y divide-slate-200 border border-slate-200 rounded bg-white" role="list">
      {documents.map((d) => {
        const selected = selectedId === d.id;
        const clickable = onSelect != null && d.status === 'ready';
        const inner = (
          <div className="flex items-center justify-between gap-3 w-full">
            <div className="min-w-0 text-left">
              <p className="font-medium truncate">{d.title}</p>
              <p className="text-xs text-slate-500">
                {d.source_type.toUpperCase()}
                {d.page_count != null && ` · ${d.page_count} ${t('documents.pages')}`}
                {d.source_language && ` · ${d.source_language}`}
              </p>
              {d.status === 'failed' && d.error_message && (
                <p role="alert" className="mt-1 text-xs text-red-700 truncate">
                  {d.error_message}
                </p>
              )}
            </div>
            <span
              className={`text-xs px-2 py-1 rounded ${STATUS_CLASS[d.status]}`}
              aria-label={t(`documents.status.${d.status}`)}
            >
              {t(`documents.status.${d.status}`)}
            </span>
          </div>
        );

        return (
          <li key={d.id}>
            {clickable ? (
              <button
                type="button"
                onClick={() => onSelect(d)}
                aria-pressed={selected}
                className={`w-full text-left p-3 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-inset ${
                  selected ? 'bg-slate-100' : ''
                }`}
              >
                {inner}
              </button>
            ) : (
              <div className="p-3">{inner}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
