import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { useRag } from '../../hooks/useRag';
import type { ChunkRef, Citation, DocumentSummary } from '../../types';
import { MessageInput } from './MessageInput';
import { MessageList } from './MessageList';

interface Props {
  document: DocumentSummary | null;
  accessToken: string | null;
  onCitationJump?: (citation: Citation, chunk: ChunkRef | undefined) => void;
}

export function ChatPanel({ document, accessToken, onCitationJump }: Props) {
  const { t } = useTranslation();
  const { phase, messages, ask, reset } = useRag(accessToken);

  // Reset on doc change — questions are single-document scoped.
  useEffect(() => {
    reset();
  }, [document?.id, reset]);

  if (!document) {
    return (
      <p className="text-slate-500" role="status">
        {t('chat.pickDocument')}
      </p>
    );
  }

  if (document.status !== 'ready') {
    return (
      <div className="text-slate-600">
        <p className="font-medium">{document.title}</p>
        <p className="text-sm mt-1">
          {t('chat.notReady', {
            status: t(`documents.status.${document.status}`),
          })}
        </p>
      </div>
    );
  }

  const busy = phase === 'asking' || phase === 'streaming';

  return (
    <section
      aria-label={t('chat.regionLabel')}
      className="flex flex-col bg-slate-50 border border-slate-200 rounded overflow-hidden h-full min-h-[400px]"
    >
      <header className="px-3 py-2 border-b border-slate-200 bg-white flex items-center justify-between">
        <div className="min-w-0">
          <p className="font-medium truncate">{document.title}</p>
          <p className="text-xs text-slate-500">
            {document.source_type.toUpperCase()}
            {document.page_count != null && ` · ${document.page_count} ${t('documents.pages')}`}
          </p>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={reset}
            className="text-xs border border-slate-300 rounded px-2 py-1 bg-white"
          >
            {t('chat.clear')}
          </button>
        )}
      </header>

      <div className="flex-1 overflow-y-auto p-3">
        <MessageList
          messages={messages}
          busy={busy}
          accessToken={accessToken}
          documentLanguageHint={document.source_language}
          onCitationJump={onCitationJump}
        />
      </div>

      <MessageInput disabled={!accessToken} busy={busy} onSubmit={(q) => ask(document.id, q)} />
    </section>
  );
}
