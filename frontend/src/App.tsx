import { type FormEvent, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ChatPanel } from './components/Chat/ChatPanel';
import { ConsentBanner } from './components/Common/ConsentBanner';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import { LoadingState } from './components/Common/LoadingState';
import { DocumentList } from './components/Documents/DocumentList';
import { DocumentViewer } from './components/Document/DocumentViewer';
import { Footer } from './components/Layout/Footer';
import { Dropzone } from './components/Upload/Dropzone';
import { useAuth } from './hooks/useAuth';
import { useDocuments } from './hooks/useDocuments';
import type { ChunkRef, Citation, CitationJump, DocumentSummary } from './types';

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
] as const;

function LangSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language.startsWith('hi') ? 'hi' : 'en';
  return (
    <select
      aria-label="Language"
      value={current}
      onChange={(e) => void i18n.changeLanguage(e.target.value)}
      className="text-sm px-2 py-1 rounded border border-slate-300 bg-white"
    >
      {LANGS.map((l) => (
        <option key={l.code} value={l.code}>
          {l.label}
        </option>
      ))}
    </select>
  );
}

function SignInForm() {
  const { t } = useTranslation();
  const { signInWithEmail, signInWithGoogle } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await signInWithEmail(email.trim());
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <p role="status" className="text-sm text-green-800">
        {t('auth.checkInbox')}
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 max-w-sm">
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium">{t('auth.signInWithEmail')}</span>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t('auth.emailPlaceholder')}
          className="border border-slate-300 rounded px-3 py-2"
        />
      </label>
      <button
        type="submit"
        disabled={submitting}
        className="bg-slate-900 text-white rounded px-4 py-2 disabled:opacity-50"
      >
        {t('auth.signIn')}
      </button>
      <button
        type="button"
        onClick={() => void signInWithGoogle()}
        className="border border-slate-300 rounded px-4 py-2 bg-white"
      >
        {t('auth.signInWithGoogle')}
      </button>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
    </form>
  );
}

export default function App() {
  const { t } = useTranslation();
  const { user, session, loading, signOut } = useAuth();
  const accessToken = session?.access_token ?? null;
  const docs = useDocuments(accessToken);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<CitationJump | null>(null);

  const selectedDoc = useMemo<DocumentSummary | null>(() => {
    if (!selectedId) return null;
    return docs.documents.find((d) => d.id === selectedId) ?? null;
  }, [selectedId, docs.documents]);

  const handleSelect = useCallback((d: DocumentSummary) => {
    setSelectedId(d.id);
    setHighlight(null);
  }, []);

  const handleCitationJump = useCallback((citation: Citation, chunk: ChunkRef | undefined) => {
    setHighlight({ citation, chunk, nonce: Date.now() });
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:bg-white focus:px-3 focus:py-1 focus:rounded focus:shadow"
      >
        {t('a11y.skipToMain')}
      </a>
      <header className="px-4 py-3 border-b border-slate-200 flex items-center justify-between bg-white">
        <div>
          <h1 className="text-lg font-bold">{t('app.name')}</h1>
          <p className="text-xs text-slate-600">{t('app.tagline')}</p>
        </div>
        <div className="flex items-center gap-3">
          <LangSwitcher />
          {user && (
            <button
              type="button"
              onClick={() => void signOut()}
              className="text-sm border border-slate-300 rounded px-3 py-1 bg-white"
            >
              {t('auth.signOut')}
            </button>
          )}
        </div>
      </header>
      <main id="main" className="flex-1 p-4 md:p-6 max-w-[1400px] mx-auto w-full">
        {loading ? (
          <LoadingState />
        ) : user && accessToken ? (
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] gap-4 lg:gap-6">
            <aside className="space-y-4">
              <Dropzone accessToken={accessToken} onUploaded={docs.refresh} />
              <section aria-labelledby="documents-heading">
                <h2 id="documents-heading" className="text-sm font-bold mb-2 text-slate-700">
                  {t('documents.heading')}
                </h2>
                <DocumentList
                  documents={docs.documents}
                  loading={docs.loading}
                  error={docs.error}
                  selectedId={selectedId}
                  onSelect={handleSelect}
                />
              </section>
            </aside>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 min-h-[600px]">
              <section
                aria-labelledby="viewer-heading"
                className="bg-white border border-slate-200 rounded overflow-hidden flex flex-col min-h-[400px] xl:min-h-[600px]"
              >
                <h2
                  id="viewer-heading"
                  className="text-sm font-bold px-3 py-2 border-b border-slate-200 text-slate-700"
                >
                  {t('viewer.heading')}
                </h2>
                <div className="flex-1 min-h-0">
                  <ErrorBoundary>
                    <DocumentViewer document={selectedDoc} highlight={highlight} />
                  </ErrorBoundary>
                </div>
              </section>
              <section
                aria-labelledby="chat-heading"
                className="min-h-[400px] xl:min-h-[600px] flex flex-col"
              >
                <h2 id="chat-heading" className="text-sm font-bold mb-2 text-slate-700">
                  {t('chat.heading')}
                </h2>
                <div className="flex-1">
                  <ErrorBoundary>
                    <ChatPanel
                      document={selectedDoc}
                      accessToken={accessToken}
                      onCitationJump={handleCitationJump}
                    />
                  </ErrorBoundary>
                </div>
              </section>
            </div>
          </div>
        ) : (
          <SignInForm />
        )}
      </main>
      <Footer accessToken={accessToken} onSignedOut={() => void signOut()} />
      <ConsentBanner />
    </div>
  );
}
