import { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

import type { CitationJump } from '../../types';
import { BboxOverlay } from './BboxOverlay';

// Configure pdfjs worker. Vite's `?url` import returns a hashed asset path
// served from the same origin — keeps CSP `worker-src 'self'` happy.
pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

interface Props {
  /** Signed URL from Supabase Storage. */
  src: string;
  /** Triggers scroll + highlight when changed. */
  highlight: CitationJump | null;
  /** Render width in pixels (page is scaled to fit). */
  width?: number;
}

export default function PdfViewer({ src, highlight, width = 720 }: Props) {
  const [numPages, setNumPages] = useState<number | null>(null);
  // scale per page = width / native_point_width
  const [pageScales, setPageScales] = useState<Record<number, number>>({});
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Scroll to the highlighted page whenever the citation changes.
  useEffect(() => {
    if (!highlight?.chunk) return;
    const target = pageRefs.current.get(highlight.chunk.page_number);
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [highlight]);

  if (!src) return null;

  return (
    <div className="overflow-y-auto h-full bg-slate-100 p-2">
      <Document
        file={src}
        loading={<p className="text-slate-500 p-4">Loading PDF…</p>}
        error={<p className="text-red-700 p-4">Failed to load PDF.</p>}
        onLoadSuccess={({ numPages }) => setNumPages(numPages)}
      >
        {numPages != null &&
          Array.from({ length: numPages }, (_, i) => i + 1).map((p) => {
            const scale = pageScales[p];
            const boxes = highlight?.chunk?.bbox?.filter((b) => b.page === p) ?? [];
            return (
              <div
                key={p}
                ref={(el) => {
                  if (el) pageRefs.current.set(p, el);
                  else pageRefs.current.delete(p);
                }}
                className="relative mx-auto mb-2 w-fit shadow-md"
              >
                <Page
                  pageNumber={p}
                  width={width}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  onLoadSuccess={(page) => {
                    const viewport = page.getViewport({ scale: 1 });
                    setPageScales((prev) =>
                      prev[p] ? prev : { ...prev, [p]: width / viewport.width },
                    );
                  }}
                />
                {scale && boxes.length > 0 && <BboxOverlay boxes={boxes} scale={scale} />}
              </div>
            );
          })}
      </Document>
    </div>
  );
}
