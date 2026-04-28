import type { ReactNode } from 'react';

interface Props {
  title: string;
  description?: string;
  action?: ReactNode;
}

/**
 * Standard "nothing here yet" surface. Day 19 reusable wrapper so every
 * empty state in the app shares the same shape and a11y semantics.
 */
export function EmptyState({ title, description, action }: Props) {
  return (
    <div
      role="status"
      className="border border-dashed border-slate-300 rounded p-6 text-center bg-white"
    >
      <p className="font-medium text-slate-700">{title}</p>
      {description && (
        <p className="text-sm text-slate-500 mt-1">{description}</p>
      )}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
