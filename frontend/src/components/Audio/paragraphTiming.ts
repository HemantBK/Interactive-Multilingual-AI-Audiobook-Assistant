/**
 * Paragraph-time estimation for the per-paragraph highlight (Day 17).
 *
 * We estimate per-paragraph duration from character count + language-specific
 * speaking rate, then calibrate against the real audio.duration once metadata
 * loads. This gives ~5–10% drift over a long passage — good enough for
 * "which paragraph is the speaker on" without backend timing capture.
 *
 * Day 21+ replaces this with edge-tts WordBoundary timestamps captured at
 * synthesis time and shipped in the TTS response. Until then, this is the
 * minimum-viable highlight.
 */

// Empirical chars/sec averages for the priority languages. Conservative
// defaults — better to highlight the previous paragraph slightly into the
// next than vice-versa.
const CHARS_PER_SEC: Readonly<Record<string, number>> = {
  en: 15,
  hi: 12,
  ta: 10,
  bn: 11,
  mr: 11,
  te: 10,
};

const DEFAULT_CHARS_PER_SEC = 13;

export interface ParagraphRange {
  start: number; // seconds
  end: number;
}

export function splitParagraphs(text: string): string[] {
  return text
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

export function estimateParagraphDurations(paragraphs: string[], language: string): number[] {
  const rate = CHARS_PER_SEC[language] ?? DEFAULT_CHARS_PER_SEC;
  return paragraphs.map((p) => Math.max(0.5, p.length / rate));
}

export function rangesFromDurations(durations: number[]): ParagraphRange[] {
  let cursor = 0;
  return durations.map((d) => {
    const r = { start: cursor, end: cursor + d };
    cursor += d;
    return r;
  });
}

/**
 * Scale ranges so the last paragraph's end matches `actualTotalSec`.
 * Used after `loadedmetadata` fires on the audio element.
 */
export function calibrate(ranges: ParagraphRange[], actualTotalSec: number): ParagraphRange[] {
  if (ranges.length === 0) return ranges;
  const estimated = ranges[ranges.length - 1].end;
  if (!Number.isFinite(actualTotalSec) || actualTotalSec <= 0 || estimated <= 0) {
    return ranges;
  }
  const scale = actualTotalSec / estimated;
  return ranges.map((r) => ({ start: r.start * scale, end: r.end * scale }));
}

export function findActiveParagraphIndex(
  ranges: ParagraphRange[],
  currentTimeSec: number,
): number | null {
  for (let i = 0; i < ranges.length; i++) {
    const r = ranges[i];
    if (currentTimeSec >= r.start && currentTimeSec < r.end) return i;
  }
  // Past the end → highlight the last paragraph
  if (ranges.length > 0 && currentTimeSec >= ranges[ranges.length - 1].end) {
    return ranges.length - 1;
  }
  return null;
}
