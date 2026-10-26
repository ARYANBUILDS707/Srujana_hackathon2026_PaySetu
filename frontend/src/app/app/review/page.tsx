"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  queueFilters,
  reviewCopy as copy,
  submissionStatusLabel,
  submissionStatusTone,
} from "@/content/review";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { ReviewQueueItem, ReviewQueuePage, ReviewSubmissionStatus } from "@/lib/api/types";
import { formatTimestamp } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

type Filter = ReviewSubmissionStatus | "all";

function queuePath(filter: Filter, cursor?: string): string {
  const params = new URLSearchParams({ limit: "20" });
  if (filter === "all") params.set("all", "true");
  else params.set("status", filter);
  if (cursor) params.set("cursor", cursor);
  return `/review/submissions?${params.toString()}`;
}

export default function ReviewQueuePage() {
  const [filter, setFilter] = useState<Filter>("PENDING_REVIEW");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={copy.queueTitle} description={copy.queueDescription} />
      <Notice title={copy.boundaryTitle}>{copy.boundary}</Notice>
      <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
        {queueFilters.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={filter === option.value}
            onClick={() => setFilter(option.value)}
            className={`h-10 rounded-md border px-3 text-small font-medium transition-colors duration-150 ${
              filter === option.value
                ? "border-ink bg-surface-subtle text-ink"
                : "border-rule-strong text-ink-muted hover:bg-surface-subtle hover:text-ink"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      <Queue key={filter} filter={filter} />
    </div>
  );
}

function Queue({ filter }: { filter: Filter }) {
  const first = useApiGet<ReviewQueuePage>(queuePath(filter));
  const [more, setMore] = useState<{ items: ReviewQueueItem[]; next: string | null } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  if (first.error)
    return (
      <ErrorState
        message={first.error.message}
        requestId={first.error.requestId}
        onRetry={first.reload}
      />
    );
  if (first.loading || !first.data) return <LoadingBlock label="Loading the review queue" />;

  const items = [...first.data.items, ...(more?.items ?? [])];
  const next = more ? more.next : first.data.next_cursor;
  if (items.length === 0) return <EmptyState title={copy.emptyTitle} body={copy.emptyBody} />;

  async function loadMore() {
    if (!next) return;
    setBusy(true);
    setError(null);
    try {
      const page = await api<ReviewQueuePage>(queuePath(filter, next));
      setMore((m) => ({ items: [...(m?.items ?? []), ...page.items], next: page.next_cursor }));
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <ul className="divide-y divide-rule" data-testid="review-queue">
        {items.map((item) => (
          <li
            key={item.submission_id}
            className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex min-w-0 flex-col gap-1">
              <p className="break-words text-body font-medium text-ink">
                {item.enterprise_name ?? item.udyam_number}
              </p>
              <p className="font-mono text-small text-ink-muted">{item.udyam_number}</p>
              <p className="text-small text-ink-muted">
                {copy.revision(item.revision)} · {formatTimestamp(item.submitted_at)} ·{" "}
                {copy.checks(item.checks_recorded)}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge tone={submissionStatusTone[item.status]}>
                  {submissionStatusLabel[item.status]}
                </Badge>
                {item.other_claimants > 0 ? (
                  <Badge tone="warning">{copy.duplicateBadge(item.other_claimants)}</Badge>
                ) : null}
                {item.claim_contested ? <Badge tone="warning">{copy.contestedBadge}</Badge> : null}
                {item.own_submission ? <Badge tone="neutral">{copy.ownBadge}</Badge> : null}
              </div>
            </div>
            <Link
              href={`/app/review/${encodeURIComponent(item.submission_id)}`}
              className="flex h-10 shrink-0 items-center justify-center rounded-md border border-rule-strong px-4 text-small font-medium text-ink transition-colors duration-150 hover:border-ink hover:bg-surface-subtle"
            >
              {copy.open}
              <span className="sr-only"> {item.enterprise_name ?? item.udyam_number}</span>
            </Link>
          </li>
        ))}
      </ul>
      {error ? (
        <div className="mt-4">
          <Notice tone="danger">{error.message}</Notice>
        </div>
      ) : null}
      {next ? (
        <div className="mt-4">
          <Button variant="secondary" disabled={busy} onClick={() => void loadMore()}>
            {copy.loadMore}
          </Button>
        </div>
      ) : null}
    </Card>
  );
}
