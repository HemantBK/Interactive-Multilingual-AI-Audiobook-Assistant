import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  calibrate,
  estimateParagraphDurations,
  findActiveParagraphIndex,
  rangesFromDurations,
  type ParagraphRange,
} from './paragraphTiming';

interface Props {
  src: string;
  mimeType: string;
  /** Already-split paragraphs (caller controls rendering of the text). */
  paragraphs: string[];
  /** Two-letter language code for rate estimation. */
  language: string;
  onActiveParagraphChange: (idx: number | null) => void;
  onEnded?: () => void;
}

const SEEK_SECONDS = 5;
const VOLUME_STEP = 0.1;

/**
 * `<audio>` wrapper that:
 *   - autoplays once mounted
 *   - emits the active paragraph index on every timeupdate
 *   - handles keyboard shortcuts when focused (or document-wide when player is the only audio)
 *
 * Keyboard map (matches YouTube / podcast-app conventions):
 *   Space, K           → play/pause
 *   ←  / J             → seek -5s
 *   →  / L             → seek +5s
 *   ↑                  → volume +10%
 *   ↓                  → volume -10%
 *   M                  → mute toggle
 *   0                  → seek to start
 */
export function AudioPlayer({
  src,
  mimeType,
  paragraphs,
  language,
  onActiveParagraphChange,
  onEnded,
}: Props) {
  const { t } = useTranslation();
  const audioRef = useRef<HTMLAudioElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const baseRanges = useMemo<ParagraphRange[]>(
    () => rangesFromDurations(estimateParagraphDurations(paragraphs, language)),
    [paragraphs, language],
  );
  const [ranges, setRanges] = useState<ParagraphRange[]>(baseRanges);

  // Reset calibration when paragraphs / language change.
  useEffect(() => {
    setRanges(baseRanges);
  }, [baseRanges]);

  // Calibrate ranges against the real audio duration.
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handler = () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        setRanges((prev) => calibrate(prev, audio.duration));
      }
    };
    audio.addEventListener('loadedmetadata', handler);
    return () => audio.removeEventListener('loadedmetadata', handler);
  }, []);

  // Highlight tracking.
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handler = () => {
      const idx = findActiveParagraphIndex(ranges, audio.currentTime);
      onActiveParagraphChange(idx);
    };
    audio.addEventListener('timeupdate', handler);
    return () => audio.removeEventListener('timeupdate', handler);
  }, [ranges, onActiveParagraphChange]);

  // Cleanup highlight on stop.
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onEndedHandler = () => {
      onActiveParagraphChange(null);
      onEnded?.();
    };
    audio.addEventListener('ended', onEndedHandler);
    return () => audio.removeEventListener('ended', onEndedHandler);
  }, [onActiveParagraphChange, onEnded]);

  // Pause on unmount — leaving audio playing in the background is rude.
  useEffect(
    () => () => {
      audioRef.current?.pause();
      onActiveParagraphChange(null);
    },
    [onActiveParagraphChange],
  );

  // Keyboard shortcuts on the wrapper.
  useEffect(() => {
    const wrapper = wrapperRef.current;
    const audio = audioRef.current;
    if (!wrapper || !audio) return;

    function handle(e: KeyboardEvent) {
      // Don't hijack typing in inputs/textareas.
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }
      if (!audio) return;
      switch (e.key) {
        case ' ':
        case 'k':
        case 'K':
          e.preventDefault();
          if (audio.paused) void audio.play();
          else audio.pause();
          break;
        case 'ArrowLeft':
        case 'j':
        case 'J':
          e.preventDefault();
          audio.currentTime = Math.max(0, audio.currentTime - SEEK_SECONDS);
          break;
        case 'ArrowRight':
        case 'l':
        case 'L':
          e.preventDefault();
          audio.currentTime = Math.min(
            Number.isFinite(audio.duration) ? audio.duration : audio.currentTime,
            audio.currentTime + SEEK_SECONDS,
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          audio.volume = Math.min(1, audio.volume + VOLUME_STEP);
          break;
        case 'ArrowDown':
          e.preventDefault();
          audio.volume = Math.max(0, audio.volume - VOLUME_STEP);
          break;
        case 'm':
        case 'M':
          e.preventDefault();
          audio.muted = !audio.muted;
          break;
        case '0':
          e.preventDefault();
          audio.currentTime = 0;
          break;
      }
    }

    wrapper.addEventListener('keydown', handle);
    return () => wrapper.removeEventListener('keydown', handle);
  }, []);

  return (
    <div
      ref={wrapperRef}
      tabIndex={0}
      role="region"
      aria-label={t('audio.playerLabel')}
      className="mt-2 outline-none focus-visible:ring-2 focus-visible:ring-slate-900 rounded"
    >
      <audio
        ref={audioRef}
        controls
        autoPlay
        src={src}
        // Using `src` attr directly; the optional <source> child below is a
        // belt-and-suspenders for browsers that prefer typed sources.
        className="w-full"
      >
        <source src={src} type={mimeType} />
        {t('audio.unsupported')}
      </audio>
      <p className="text-[10px] text-slate-400 mt-1">{t('audio.keyboardHint')}</p>
    </div>
  );
}
