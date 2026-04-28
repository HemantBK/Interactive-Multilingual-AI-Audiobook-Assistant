import { type FormEvent, type KeyboardEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  disabled?: boolean;
  busy?: boolean;
  onSubmit: (question: string) => void | Promise<void>;
}

export function MessageInput({ disabled, busy, onSubmit }: Props) {
  const { t } = useTranslation();
  const [text, setText] = useState('');

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy || disabled) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    setText('');
    await onSubmit(trimmed);
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      form?.requestSubmit();
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-2 items-end border-t border-slate-200 bg-white p-3"
    >
      <label className="flex-1">
        <span className="sr-only">{t('chat.questionLabel')}</span>
        <textarea
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled || busy}
          placeholder={t('chat.placeholder')}
          className="w-full resize-none border border-slate-300 rounded px-3 py-2 disabled:bg-slate-50 disabled:cursor-not-allowed"
        />
      </label>
      <button
        type="submit"
        disabled={disabled || busy || !text.trim()}
        className="bg-slate-900 text-white rounded px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed h-10"
      >
        {busy ? t('chat.sendBusy') : t('chat.send')}
      </button>
    </form>
  );
}
