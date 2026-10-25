import type { ReactNode } from "react";

/** Native, keyboard-accessible expandable explanation (used for "Why this date?"). */
export function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="group mt-1">
      <summary className="inline-flex w-fit cursor-pointer list-none items-center gap-1 rounded-md text-small font-medium text-info hover:text-primary [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden="true"
          className="inline-block text-caption transition-transform duration-150 group-open:rotate-90"
        >
          ▸
        </span>
        {summary}
      </summary>
      <div className="mt-2 rounded-md border border-rule bg-surface-subtle p-3 text-small text-ink">
        {children}
      </div>
    </details>
  );
}
