import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { API_BASE_URL } from '../../services/api';
import { useToast } from '../Common/Toast';

interface Props {
  accessToken: string | null;
  onSignedOut: () => void;
}

/**
 * Footer with legal links + account self-service (Day 25).
 *
 *   Privacy / Terms / DMCA → static markdown in docs/legal/* on GitHub
 *   Export my data         → GET  /user/me/export, downloads JSON
 *   Delete my account      → DELETE /user/me, requires confirmation
 *
 * For v1 the legal docs are linked rather than rendered in-app — the
 * audience and scope don't justify a markdown viewer route yet.
 */
export function Footer({ accessToken, onSignedOut }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const [busy, setBusy] = useState<'export' | 'delete' | null>(null);

  // Static URLs — repo is public; legal docs ship in-tree.
  const REPO = 'https://github.com/hemantkumar/aria';
  const privacyUrl = `${REPO}/blob/main/docs/legal/privacy.md`;
  const termsUrl = `${REPO}/blob/main/docs/legal/terms.md`;
  const dmcaUrl = `${REPO}/blob/main/docs/legal/dmca.md`;

  async function handleExport() {
    if (!accessToken) return;
    setBusy('export');
    try {
      const res = await fetch(`${API_BASE_URL}/user/me/export`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) {
        toast.error(t('account.exportFailed', { status: res.status }));
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aria-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t('account.exportDone'));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete() {
    if (!accessToken) return;
    if (!window.confirm(t('account.deleteConfirm'))) return;
    setBusy('delete');
    try {
      const res = await fetch(`${API_BASE_URL}/user/me`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok && res.status !== 204) {
        toast.error(t('account.deleteFailed', { status: res.status }));
        return;
      }
      toast.success(t('account.deleteDone'));
      onSignedOut();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <footer className="border-t border-slate-200 bg-white px-4 py-3 mt-6">
      <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-slate-600">
        <nav aria-label={t('footer.legalNav')} className="flex flex-wrap gap-3">
          <a href={privacyUrl} className="hover:text-slate-900 underline" target="_blank" rel="noopener noreferrer">
            {t('footer.privacy')}
          </a>
          <a href={termsUrl} className="hover:text-slate-900 underline" target="_blank" rel="noopener noreferrer">
            {t('footer.terms')}
          </a>
          <a href={dmcaUrl} className="hover:text-slate-900 underline" target="_blank" rel="noopener noreferrer">
            {t('footer.dmca')}
          </a>
        </nav>
        {accessToken && (
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleExport()}
              disabled={busy !== null}
              className="hover:text-slate-900 underline disabled:opacity-50"
            >
              {busy === 'export' ? t('account.exporting') : t('account.exportLink')}
            </button>
            <button
              type="button"
              onClick={() => void handleDelete()}
              disabled={busy !== null}
              className="text-red-700 hover:text-red-900 underline disabled:opacity-50"
            >
              {busy === 'delete' ? t('account.deleting') : t('account.deleteLink')}
            </button>
          </div>
        )}
      </div>
    </footer>
  );
}
