import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';

/**
 * Minimal in-house toast system (build plan A2 §12 Day 19).
 *
 * Why not pull `react-hot-toast` / `sonner`: ~80 lines avoids another
 * 3rd-party dep + license vetting. Same UX shape, less surface.
 *
 * Toasts auto-dismiss after `AUTO_DISMISS_MS`. Errors use role="alert"
 * so screen readers announce them; success / info use role="status".
 */

export type ToastVariant = 'success' | 'error' | 'info';

interface Toast {
  id: string;
  variant: ToastVariant;
  message: string;
}

interface ToastContextValue {
  push: (variant: ToastVariant, message: string) => void;
  success: (msg: string) => void;
  error: (msg: string) => void;
  info: (msg: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);
const AUTO_DISMISS_MS = 5_000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (variant: ToastVariant, message: string) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, variant, message }]);
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  const value: ToastContextValue = useMemo(
    () => ({
      push,
      success: (msg) => push('success', msg),
      error: (msg) => push('error', msg),
      info: (msg) => push('info', msg),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used inside <ToastProvider>');
  }
  return ctx;
}

const VARIANT_CLASS: Record<ToastVariant, string> = {
  success: 'bg-green-50 border-green-400 text-green-900',
  error: 'bg-red-50 border-red-400 text-red-900',
  info: 'bg-slate-50 border-slate-300 text-slate-900',
};

function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  const { t } = useTranslation();
  if (toasts.length === 0) return null;
  return (
    <div
      aria-label={t('toast.regionLabel')}
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const { t } = useTranslation();
  // Mount-time fade-in; CSS keeps the markup tiny.
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const id = window.setTimeout(() => setVisible(true), 10);
    return () => window.clearTimeout(id);
  }, []);

  return (
    <div
      role={toast.variant === 'error' ? 'alert' : 'status'}
      className={[
        'border rounded shadow-md px-3 py-2 text-sm flex items-start gap-2',
        VARIANT_CLASS[toast.variant],
        'transition-opacity duration-200',
        visible ? 'opacity-100' : 'opacity-0',
      ].join(' ')}
    >
      <p className="flex-1 break-words">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label={t('toast.dismiss')}
        className="text-current opacity-60 hover:opacity-100 px-1"
      >
        ×
      </button>
    </div>
  );
}
