import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';

import type {
  AssistantMessage,
  ChatMessage,
  ChunkRef,
  Citation,
} from '../../types';
import { NarrateButton } from '../Audio/NarrateButton';
import { splitParagraphs } from '../Audio/paragraphTiming';
import { CitationCard } from './CitationCard';
import { TranslateMenu, type TranslationView } from './TranslateMenu';

// react-markdown is XSS-safe by default — it does NOT render raw HTML
// (rehype-raw is opt-in, we don't use it). We additionally pass
// `disallowedElements` for any tag react-markdown might emit from markdown
// but which we don't want in answer/translation surfaces (Day 13 hardening).
const DISALLOWED_MARKDOWN_TAGS = [
  'script',
  'iframe',
  'object',
  'embed',
  'style',
  'link',
  'meta',
  'form',
  'input',
];

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  accessToken: string | null;
  documentLanguageHint?: string | null;
  onCitationJump?: (citation: Citation, chunk: ChunkRef | undefined) => void;
}

export function MessageList({
  messages,
  busy,
  accessToken,
  documentLanguageHint,
  onCitationJump,
}: Props) {
  const { t } = useTranslation();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, busy]);

  if (messages.length === 0) {
    return <p className="text-slate-500">{t('chat.empty')}</p>;
  }

  return (
    <div
      role="log"
      aria-live="polite"
      aria-busy={busy}
      aria-label={t('chat.regionLabel')}
      className="flex flex-col gap-4"
    >
      {messages.map((m) =>
        m.role === 'user' ? (
          <UserBubble key={m.id} text={m.text} />
        ) : (
          <AssistantBubble
            key={m.id}
            message={m}
            accessToken={accessToken}
            documentLanguageHint={documentLanguageHint}
            onCitationJump={onCitationJump}
          />
        ),
      )}
      <div ref={endRef} />
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="self-end max-w-[85%] bg-slate-900 text-white px-4 py-2 rounded-2xl rounded-br-sm">
      <p className="whitespace-pre-wrap">{text}</p>
    </div>
  );
}

function SafeMarkdown({
  children,
  lang,
}: {
  children: string;
  /** ISO 639-1 — sets `lang` on the wrapper so screen readers pronounce
   * embedded snippets (Hindi answer in an English UI etc.) correctly. */
  lang?: string | null;
}) {
  return (
    <div
      lang={lang ?? undefined}
      className="prose prose-sm max-w-none [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:mb-2 [&>ol]:mb-2"
    >
      <ReactMarkdown
        disallowedElements={DISALLOWED_MARKDOWN_TAGS}
        unwrapDisallowed
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

function HighlightedParagraphs({
  paragraphs,
  activeIdx,
  lang,
}: {
  paragraphs: string[];
  activeIdx: number | null;
  lang?: string | null;
}) {
  return (
    <div lang={lang ?? undefined} className="text-sm leading-relaxed">
      {paragraphs.map((p, i) => (
        <p
          key={i}
          className={
            i === activeIdx
              ? 'bg-amber-100 -mx-1 px-1 rounded transition-colors mb-2 last:mb-0'
              : 'transition-colors mb-2 last:mb-0'
          }
        >
          {p}
        </p>
      ))}
    </div>
  );
}

function AssistantBubble({
  message,
  accessToken,
  documentLanguageHint,
  onCitationJump,
}: {
  message: AssistantMessage;
  accessToken: string | null;
  documentLanguageHint?: string | null;
  onCitationJump?: (citation: Citation, chunk: ChunkRef | undefined) => void;
}) {
  const { t } = useTranslation();
  const [translation, setTranslation] = useState<TranslationView | null>(null);
  const [narrating, setNarrating] = useState(false);
  const [activeParagraphIdx, setActiveParagraphIdx] = useState<number | null>(null);

  // The text + language presented to TTS depends on whether we have a translation.
  const narratedText = translation ? translation.text : message.text;
  const narratedLanguageHint = translation
    ? translation.langCode
    : documentLanguageHint ?? null;
  const paragraphs = useMemo(
    () => splitParagraphs(narratedText),
    [narratedText],
  );

  if (message.status === 'streaming' && !message.text) {
    return (
      <div
        role="status"
        className="self-start max-w-[85%] bg-white border border-slate-200 px-4 py-2 rounded-2xl rounded-bl-sm text-slate-500 italic"
      >
        {t('chat.thinking')}
      </div>
    );
  }

  if (message.status === 'error') {
    return (
      <div
        role="alert"
        className="self-start max-w-[85%] border border-red-300 bg-red-50 text-red-800 px-4 py-2 rounded-2xl rounded-bl-sm"
      >
        <p className="font-medium">{t('chat.errorHeading')}</p>
        <p className="text-sm mt-1">{message.error}</p>
      </div>
    );
  }

  // Per-content lang attribute so NVDA / VoiceOver speak the answer in the
  // doc's source language, even when the UI itself is English (Day 21 a11y).
  const answerLang = documentLanguageHint ?? null;
  const translationLang = translation ? translation.langCode : null;

  return (
    <div className="self-start max-w-[85%] flex flex-col gap-2">
      <div className="bg-white border border-slate-200 px-4 py-2 rounded-2xl rounded-bl-sm">
        {narrating ? (
          <HighlightedParagraphs
            paragraphs={paragraphs}
            activeIdx={activeParagraphIdx}
            lang={narratedLanguageHint}
          />
        ) : (
          <SafeMarkdown lang={answerLang}>{message.text}</SafeMarkdown>
        )}

        {translation && !narrating && (
          <div className="mt-3 pt-3 border-t border-slate-200">
            <p className="text-[11px] text-slate-500 mb-1">
              {t('chat.translate.heading', { lang: translation.langLabel })}
              {translation.cached && (
                <span className="ml-2 text-slate-400">
                  · {t('chat.translate.cached')}
                </span>
              )}
            </p>
            <SafeMarkdown lang={translationLang}>
              {translation.text}
            </SafeMarkdown>
          </div>
        )}

        {message.latencyMs != null && (
          <p className="text-[10px] text-slate-400 mt-2">
            {(message.latencyMs / 1000).toFixed(1)}s
          </p>
        )}

        {message.text.trim().length > 0 && (
          <>
            <NarrateButton
              text={narratedText}
              paragraphs={paragraphs}
              languageHint={narratedLanguageHint}
              accessToken={accessToken}
              onPlay={() => setNarrating(true)}
              onStop={() => {
                setNarrating(false);
                setActiveParagraphIdx(null);
              }}
              onActiveParagraphChange={setActiveParagraphIdx}
            />
            <TranslateMenu
              sourceText={message.text}
              sourceLanguageHint={documentLanguageHint}
              accessToken={accessToken}
              current={translation}
              onChange={(view) => {
                setTranslation(view);
                // Switching translations resets narration view.
                setNarrating(false);
                setActiveParagraphIdx(null);
              }}
            />
          </>
        )}
      </div>
      {message.citations.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {message.citations.map((c, i) => (
            <CitationCard
              key={`${message.id}-${i}`}
              citation={c}
              retrievedChunks={message.retrievedChunks}
              quoteLang={documentLanguageHint}
              onJump={onCitationJump}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
