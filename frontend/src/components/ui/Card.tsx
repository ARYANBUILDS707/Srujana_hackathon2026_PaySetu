import type { ReactNode } from "react";

export function Card({
  title,
  description,
  actions,
  children,
  className = "",
  id,
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={`scroll-mt-20 rounded-lg border border-rule bg-surface p-4 md:p-6 ${className}`}
    >
      {title ? (
        <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-h3 text-ink">{title}</h2>
            {description ? <p className="mt-1 text-small text-ink-muted">{description}</p> : null}
          </div>
          {actions}
        </header>
      ) : null}
      {children}
    </section>
  );
}
