import { useEffect, useRef, useState } from 'react';

import type { CitationJump } from '../../types';
import { BboxOverlay } from './BboxOverlay';

interface Props {
  src: string;
  highlight: CitationJump | null;
  alt?: string;
}

export default function ImageViewer({ src, highlight, alt = '' }: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [naturalWidth, setNaturalWidth] = useState<number | null>(null);
  const [renderedWidth, setRenderedWidth] = useState<number | null>(null);

  // Recompute scale on resize so the bbox overlay tracks the rendered <img>.
  useEffect(() => {
    if (!imgRef.current) return;
    const observer = new ResizeObserver(() => {
      if (imgRef.current) setRenderedWidth(imgRef.current.clientWidth);
    });
    observer.observe(imgRef.current);
    return () => observer.disconnect();
  }, [src]);

  // Scroll to the image when the citation changes (single "page" for images).
  useEffect(() => {
    if (highlight?.chunk) {
      wrapperRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [highlight]);

  const scale = naturalWidth && renderedWidth ? renderedWidth / naturalWidth : 0;
  const boxes = highlight?.chunk?.bbox?.filter((b) => b.page === 1) ?? [];

  return (
    <div ref={wrapperRef} className="overflow-y-auto h-full bg-slate-100 p-2">
      <div className="relative mx-auto w-fit shadow-md">
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          onLoad={(e) => {
            const el = e.currentTarget;
            setNaturalWidth(el.naturalWidth);
            setRenderedWidth(el.clientWidth);
          }}
          className="max-w-full block"
        />
        {scale > 0 && boxes.length > 0 && <BboxOverlay boxes={boxes} scale={scale} />}
      </div>
    </div>
  );
}
