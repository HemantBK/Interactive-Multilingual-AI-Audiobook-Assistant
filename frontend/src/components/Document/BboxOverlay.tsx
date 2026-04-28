import type { BBox } from '../../types';

interface Props {
  /** Boxes to render. Caller has already filtered by page if needed. */
  boxes: BBox[];
  /** Pixels per source unit (PDF point or image pixel). */
  scale: number;
}

/**
 * Renders translucent yellow rectangles on top of a positioned ancestor
 * (caller wraps in `position: relative`). Pure presentation; coordinate
 * filtering is the caller's responsibility.
 */
export function BboxOverlay({ boxes, scale }: Props) {
  if (boxes.length === 0 || scale <= 0) return null;
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0"
      style={{ position: 'absolute', inset: 0 }}
    >
      {boxes.map((b, i) => (
        <div
          key={`${b.x0}-${b.y0}-${i}`}
          className="absolute bg-amber-300/40 ring-1 ring-amber-500/60 rounded-sm"
          style={{
            left: b.x0 * scale,
            top: b.y0 * scale,
            width: Math.max(1, (b.x1 - b.x0) * scale),
            height: Math.max(1, (b.y1 - b.y0) * scale),
          }}
        />
      ))}
    </div>
  );
}
