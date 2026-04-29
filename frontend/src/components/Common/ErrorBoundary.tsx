import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { captureException } from '../../lib/sentry';

/**
 * Catches render-time errors in a sub-tree and renders a fallback. Per-section
 * wrap (used in App.tsx): a viewer crash doesn't take down the chat panel.
 * Top-level wrap (in main.tsx) catches the remainder.
 *
 * Day 22 wires Sentry into componentDidCatch (no-op when DSN absent).
 */

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', error, info.componentStack);
    captureException(error, { componentStack: info.componentStack });
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    if (this.props.fallback) return this.props.fallback(this.state.error, this.reset);
    return <DefaultFallback error={this.state.error} onReset={this.reset} />;
  }
}

function DefaultFallback({ error, onReset }: { error: Error; onReset: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="border border-red-300 bg-red-50 text-red-900 p-4 rounded">
      <h2 className="font-bold">{t('errors.boundary.title')}</h2>
      <p className="text-sm mt-1 break-words">{error.message}</p>
      <button type="button" onClick={onReset} className="mt-3 text-sm underline">
        {t('errors.boundary.retry')}
      </button>
    </div>
  );
}
