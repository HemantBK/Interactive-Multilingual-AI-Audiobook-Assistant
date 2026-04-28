import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from './hooks/useAuth';

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
      <p role="status" className="text-sm text-green-700">
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
  const { user, loading, signOut } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
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
      <main className="flex-1 p-8 max-w-3xl mx-auto w-full">
        {loading ? (
          <p role="status" className="text-slate-500">
            …
          </p>
        ) : user ? (
          <div>
            <p className="mb-2">
              {t('auth.signedInAs')} <strong>{user.email}</strong>
            </p>
            <p className="text-slate-600">{t('comingSoon')}</p>
          </div>
        ) : (
          <SignInForm />
        )}
      </main>
    </div>
  );
}
