"use client";

import { useParams } from "next/navigation";
import { Card } from "@/components/ui/Card";
import { HashChip } from "@/components/ui/HashChip";
import { ErrorState, LoadingBlock } from "@/components/ui/Notice";
import { eventTypeLabel } from "@/content/app";
import type { TimelineEvent } from "@/lib/api/types";
import { formatDate, formatTimestamp } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function TimelinePage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApiGet<TimelineEvent[]>(
    `/cases/${params.id}/timeline`,
  );

  if (error)
    return <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />;
  if (loading || !data) return <LoadingBlock label="Loading timeline" />;

  return (
    <Card
      title="Timeline"
      description="Every action is recorded in order. Each entry carries a hash that includes the entry before it, so a later change to history can be detected."
    >
      <ol className="divide-y divide-rule" data-testid="timeline-list">
        {[...data].reverse().map((event) => (
          <li
            key={event.seq}
            className="flex flex-col gap-2 py-4 md:flex-row md:items-start md:justify-between"
          >
            <div>
              <p className="text-body font-medium text-ink">
                #{event.seq} · {eventTypeLabel[event.event_type] ?? event.event_type}
              </p>
              <p className="text-small text-ink-muted">
                {formatTimestamp(event.recorded_at)} · {event.actor_type.replace("_", " ")}
                {event.occurred_on ? ` · refers to ${formatDate(event.occurred_on)}` : ""}
              </p>
            </div>
            <HashChip hash={event.event_hash} label="Event" />
          </li>
        ))}
      </ol>
    </Card>
  );
}
