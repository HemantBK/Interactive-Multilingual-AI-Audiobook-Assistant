import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { track } from '../../lib/analytics';
import { ApiError, synthesizeTTS } from '../../services/api';
import { AudioPlayer } from './AudioPlayer';
import { VoicePicker } from './VoicePicker';
import { defaultVoiceIdForLanguage } from './voices';

interface Props {
  text: string;
  /** Already-split paragraphs (parent controls how they render). */
  paragraphs: string[];
  /** ISO 639-1 hint, e.g. document.source_language. */
  languageHint?: string | null;
  accessToken: string | null;
  /** Fired with the active paragraph index whenever audio is playing. */
  onActiveParagraphChange: (idx: number | null) => void;
  /** Fired when user enters narration mode (parent switches to <p> rendering). */
  onPlay: () => void;
  /** Fired when audio ends or user stops. */
  onStop: () => void;
}

interface AudioState {
  url: string;
  mimeType: string;
  language: string;
  cached: boolean;
  fallbackUsed: boolean;
}

/**
 * idle → click → loading → AudioPlayer renders + autoplays → controls take over.
 *
 * Voice override: a small picker is visible before playback. After Narrate
 * fires, voice is locked for that audio (changing voice resets state).
 */
export function NarrateButton({
  text,
  paragraphs,
  languageHint,
  accessToken,
  onActiveParagraphChange,
  onPlay,
  onStop,
}: Props) {
  const { t } = useTranslation();
  const [voiceId, setVoiceId] = useState(() => defaultVoiceIdForLanguage(languageHint ?? null));
  const [audio, setAudio] = useState<AudioState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleVoiceChange(next: string) {
    if (next === voiceId) return;
    setVoiceId(next);
    // If a previous audio is playing, drop it — voice change must re-synth.
    if (audio) {
      setAudio(null);
      onActiveParagraphChange(null);
      onStop();
    }
  }

  async function handlePlay() {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const res = await synthesizeTTS({ text, voice_id: voiceId }, accessToken);
      setAudio({
        url: res.audio_url,
        mimeType: res.mime_type,
        language: res.language,
        cached: res.cached,
        fallbackUsed: res.fallback_used,
      });
      onPlay();
      track('tts.played', {
        voice_id: voiceId,
        chars: text.length,
        cached: res.cached,
        fallback_used: res.fallback_used,
      });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `${err.status} — ${err.message}`
          : err instanceof Error
            ? err.message
            : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleStop() {
    setAudio(null);
    onActiveParagraphChange(null);
    onStop();
  }

  if (audio) {
    return (
      <div className="mt-2 flex flex-col gap-1">
        <AudioPlayer
          src={audio.url}
          mimeType={audio.mimeType}
          paragraphs={paragraphs}
          language={audio.language}
          onActiveParagraphChange={onActiveParagraphChange}
          onEnded={handleStop}
        />
        <div className="flex items-center justify-between gap-2 text-[11px]">
          <div className="flex items-center gap-2 text-slate-400">
            {audio.cached && <span>{t('audio.cached')}</span>}
            {audio.fallbackUsed && <span>· {t('audio.fallback')}</span>}
          </div>
          <button type="button" onClick={handleStop} className="text-slate-600 underline">
            {t('audio.stop')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-2 flex items-center gap-2 flex-wrap">
      <VoicePicker
        value={voiceId}
        language={languageHint ?? null}
        onChange={handleVoiceChange}
        disabled={loading || !accessToken}
      />
      <button
        type="button"
        onClick={() => void handlePlay()}
        disabled={loading || !accessToken}
        className="text-xs border border-slate-300 rounded px-2 py-1 bg-white hover:bg-slate-50 disabled:opacity-50"
        aria-label={t('audio.playLabel')}
      >
        {loading ? t('audio.busy') : t('audio.play')}
      </button>
      {error && (
        <span role="alert" className="text-[11px] text-red-700">
          {error}
        </span>
      )}
    </div>
  );
}
