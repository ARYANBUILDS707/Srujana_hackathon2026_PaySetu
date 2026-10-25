import type { ReactNode } from "react";
import { Button } from "./Button";

type NoticeTone = "info" | "success" | "warning" | "danger";

const tones: Record<NoticeTone, string> = {
  info: "border-primary bg-primary-tint text-ink",
  success: "border-success bg-success-tint text-ink",
  warning: "border-warning bg-warning-tint text-ink",
  danger: "border-danger bg-danger-tint text-ink",
};

export function Notice({
  tone = "info",
  title,
  children,
}: {
  tone?: NoticeTone;
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={`rounded-md border-l-4 p-4 text-small ${tones[tone]}`}
    >
      {title ? <p className="font-semibold text-ink">{title}</p> : null}
      {children ? <div className={title ? "mt-1" : ""}>{children}</div> : null}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div aria-hidden="true" className={`animate-pulse rounded-md bg-surface-sunken ${className}`} />
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-3">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-rule-strong bg-surface p-8 text-center">
      <p className="text-h3 text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-small text-ink-muted">{body}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  requestId,
  onRetry,
}: {
  message: string;
  requestId?: string | null;
  onRetry?: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-danger bg-danger-tint p-5">
      <p className="text-h3 text-ink">Something went wrong</p>
      <p className="mt-1 text-small text-ink">{message}</p>
      {requestId ? (
        <p className="mt-1 font-mono text-caption text-ink-muted">Request ID: {requestId}</p>
      ) : null}
      {onRetry ? (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
