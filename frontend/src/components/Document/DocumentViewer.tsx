import { Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';

import { useDocumentSource } from '../../hooks/useDocumentSource';
import type { CitationJump, DocumentSummary } from '../../types';

// Lazy-load PDF viewer — pdfjs-dist is ~3 MB and only worth pulling for PDFs.
const PdfViewer = lazy(() => import('./PdfViewer'));
const ImageViewer = lazy(() => import('./ImageViewer'));

interface Props {
  document: DocumentSummary | null;
  highlight: CitationJump | null;
}

export function DocumentViewer({ document, highlight }: Props) {
  const { t } = useTranslation();

  if (!document) {
    return (
      <p className="text-slate-500" role="status">
        {t('viewer.noDocument')}
      </p>
    );
  }

  if (document.status !== 'ready') {
    return (
      <div className="text-slate-600">
        <p className="font-medium">{document.title}</p>
        <p className="text-sm mt-1">
          {t('viewer.notReady', {
            status: t(`documents.status.${document.status}`),
          })}
        </p>
      </div>
    );
  }

  // The DocumentSummary doesn't carry storage_path, so we derive the
  // canonical layout: <user_id>/<doc_id>/original.<ext>. Day 4's upload
  // endpoint commits to this path.
  const ext = guessExt(document);
  const storagePath = `${document.user_id}/${document.id}/original.${ext}`;

  return (
    <SourceLoader
      storagePath={storagePath}
      sourceType={document.source_type}
      highlight={highlight}
      title={document.title}
    />
  );
}

function guessExt(doc: DocumentSummary): string {
  if (doc.source_type === 'pdf') return 'pdf';
  if (doc.source_type === 'text') return 'txt';
  // image: backend re-encodes via Pillow; we don't currently expose the
  // chosen ext per row. The upload path stores 'jpg' for JPEG, 'png' for
  // PNG, 'webp' for WEBP. We'll try jpg first; if 404, the viewer simply
  // shows the loader's error state.
  return 'jpg';
}

interface LoaderProps {
  storagePath: string;
  sourceType: DocumentSummary['source_type'];
  highlight: CitationJump | null;
  title: string;
}

function SourceLoader({ storagePath, sourceType, highlight, title }: LoaderProps) {
  const { t } = useTranslation();
  const { url, loading, error } = useDocumentSource(storagePath);

  if (loading) {
    return (
      <p className="text-slate-500 p-4" role="status">
        {t('viewer.loading')}
      </p>
    );
  }
  if (error || !url) {
    return (
      <p className="text-red-700 p-4" role="alert">
        {error ?? t('viewer.loadFailed')}
      </p>
    );
  }

  return (
    <Suspense
      fallback={
        <p className="text-slate-500 p-4" role="status">
          {t('viewer.loading')}
        </p>
      }
    >
      {sourceType === 'pdf' ? (
        <PdfViewer src={url} highlight={highlight} />
      ) : sourceType === 'image' ? (
        <ImageViewer src={url} highlight={highlight} alt={title} />
      ) : (
        <p className="p-4 text-slate-600">{t('viewer.textComingSoon')}</p>
      )}
    </Suspense>
  );
}
