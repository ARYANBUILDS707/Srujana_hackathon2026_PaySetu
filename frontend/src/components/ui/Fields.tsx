"use client";

import { useId, type ReactNode } from "react";

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: (control: {
    id: string;
    "aria-describedby": string | undefined;
    "aria-invalid": boolean | undefined;
  }) => ReactNode;
}

/** Label above the control, helper text below, error replaces the helper (DESIGN.md 5.2). */
export function Field({ label, hint, error, required, children }: FieldProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ?? hint;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-small font-medium text-ink">
        {label}
        {required ? <span className="text-ink-muted"> (required)</span> : null}
      </label>
      {children({
        id,
        "aria-describedby": message ? messageId : undefined,
        "aria-invalid": error ? true : undefined,
      })}
      {message ? (
        <p id={messageId} className={`text-small ${error ? "text-danger" : "text-ink-muted"}`}>
          {message}
        </p>
      ) : null}
    </div>
  );
}

export const controlClass =
  "h-11 w-full rounded-md border border-control bg-surface px-3 text-body text-ink transition-colors duration-150 placeholder:text-ink-faint hover:border-ink-muted aria-[invalid=true]:border-danger disabled:bg-surface-subtle";

export const textareaClass =
  "min-h-24 w-full rounded-md border border-control bg-surface px-3 py-2 text-body text-ink transition-colors duration-150 placeholder:text-ink-faint hover:border-ink-muted aria-[invalid=true]:border-danger";
