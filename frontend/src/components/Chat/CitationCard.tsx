import { useTranslation } from 'react-i18next';

import { track } from '../../lib/analytics';
import type { ChunkRef, Citation } from '../../types';

interface Props {
  citation: Citation;
  retrievedChunks: ChunkRef[];
  /** Source-document language for the quote (Day 21 a11y). */
  quoteLang?: string | null;
  onJump?: (citation: Citation, chunk: ChunkRef | undefined) => void;
}

/**
 * One cited passage. Click → caller scrolls the document viewer to the
 * cited page and highlights the chunk's word bboxes (Day 11 dual-citation).
 */
export function CitationCard({ citation, retrievedChunks, quoteLang, onJump }: Props) {
  const { t } = useTranslation();
  const ref = retrievedChunks.find((r) => r.id === citation.chunk_id);
  const page = ref?.page_number;

  const inner = (
    <>
      <p lang={quoteLang ?? undefined} className="text-slate-800 italic">
        “{citation.quote}”
      </p>
      {page != null && (
        <p className="mt-1 text-slate-600">
          <span className="font-medium">{t('chat.page')}</span> {page}
        </p>
      )}
    </>
  );

  if (!onJump) {
    return (
      <li className="text-xs border-l-2 border-amber-400 bg-amber-50 px-3 py-2 rounded-sm">
        {inner}
      </li>
    );
  }

  function handleClick() {
    track('rag.citation_click', {
      page_number: page ?? null,
      chunk_id: citation.chunk_id,
    });
    onJump?.(citation, ref);
  }

  return (
    <li>
      <button
        type="button"
        onClick={handleClick}
        className="w-full text-left text-xs border-l-2 border-amber-400 bg-amber-50 hover:bg-amber-100 px-3 py-2 rounded-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        aria-label={page != null ? t('chat.jumpToPage', { page }) : t('chat.jumpToCitation')}
      >
        {inner}
      </button>
    </li>
  );
}
