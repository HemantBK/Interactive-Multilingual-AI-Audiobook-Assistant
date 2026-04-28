import { type ChangeEvent, type DragEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { track } from '../../lib/analytics';
import { ApiError, createDocument } from '../../services/api';
import { useToast } from '../Common/Toast';

interface DropzoneProps {
  accessToken: string;
  onUploaded: () => void | Promise<void>;
}

const ACCEPT_MIMES = 'application/pdf,image/jpeg,image/png,image/webp,text/plain';

export function Dropzone({ accessToken, onUploaded }: DropzoneProps) {
  const { t } = useTranslation();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function uploadOne(file: File) {
    setBusy(true);
    setError(null);
    try {
      const idempotencyKey = crypto.randomUUID();
      const res = await createDocument(file, file.name, accessToken, idempotencyKey);
      await onUploaded();
      // Persistent context-bound state stays inline; transient confirmation
      // pops as a toast (build plan A2 §12 Day 19).
      toast.success(t('upload.successToast', { name: file.name }));
      track('document.uploaded', {
        source_type: res.source_type,
        size_bytes: file.size,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? `${err.status} — ${err.message}`
          : err instanceof Error
            ? err.message
            : String(err);
      setError(message);
      toast.error(t('upload.errorToast', { message }));
      track('document.upload_failed', {
        status: err instanceof ApiError ? err.status : null,
      });
    } finally {
      setBusy(false);
    }
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void uploadOne(file);
    // Reset so the same file can be re-picked after an error
    e.target.value = '';
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void uploadOne(file);
  }

  return (
    <div
      role="region"
      aria-label={t('upload.regionLabel')}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      className={`border-2 border-dashed rounded p-8 text-center transition-colors ${
        dragOver ? 'border-slate-900 bg-slate-50' : 'border-slate-300 bg-white'
      }`}
    >
      <p className="mb-3 text-slate-700">{t('upload.prompt')}</p>
      <input
        type="file"
        accept={ACCEPT_MIMES}
        onChange={onChange}
        disabled={busy}
        className="block mx-auto"
        aria-label={t('upload.inputLabel')}
      />
      <p className="mt-2 text-xs text-slate-500">{t('upload.maxSize')}</p>
      {busy && (
        <p role="status" className="mt-3 text-sm text-slate-700">
          {t('upload.uploading')}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
