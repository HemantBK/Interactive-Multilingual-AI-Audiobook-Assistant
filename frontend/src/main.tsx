import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import { ErrorBoundary } from './components/Common/ErrorBoundary';
import { ToastProvider } from './components/Common/Toast';
import './i18n';
import { initAnalytics } from './lib/analytics';
import { initSentry } from './lib/sentry';

// Day 22: observability boots before React mounts so the very first error
// — including ones thrown during render — is captured.
initSentry();
initAnalytics();

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('root element missing');
}

createRoot(rootEl).render(
  <StrictMode>
    <ToastProvider>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </ToastProvider>
  </StrictMode>,
);
