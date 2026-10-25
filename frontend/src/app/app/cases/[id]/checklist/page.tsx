"use client";

import { useParams } from "next/navigation";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { checklistStatusLabel } from "@/content/app";
import type { Checklist, ChecklistItem } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

const tone: Record<string, Tone> = {
  met: "success",
  missing: "warning",
  warning: "warning",
  not_applicable: "neutral",
};

export default function ChecklistPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApiGet<Checklist>(`/cases/${params.id}/checklist`);

  if (error)
    return <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />;
  if (loading || !data) return <LoadingBlock label="Loading checklist" />;

  const required = data.items.filter((i) => i.level === "required");
  const recommended = data.items.filter((i) => i.level === "recommended");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-h2 text-ink" data-testid="checklist-heading">
          {data.required_met} of {data.required_total} required items complete
        </h2>
        <p className="mt-1 text-small text-ink-muted">
          A readiness list of what is in your file. It does not score the case or predict any
          outcome.
        </p>
      </div>
      <Card title="Required">
        <ItemList items={required} />
      </Card>
      <Card title="Recommended">
        <ItemList items={recommended} />
      </Card>
      {data.unconfirmed_rules.length > 0 ? (
        <Notice tone="warning" title="Pending legal review">
          Rules still awaiting an advocate&apos;s confirmation:{" "}
          <span className="font-mono">{data.unconfirmed_rules.join(", ")}</span>.
        </Notice>
      ) : null}
    </div>
  );
}

function ItemList({ items }: { items: ChecklistItem[] }) {
  return (
    <ul className="divide-y divide-rule">
      {items.map((item) => (
        <li
          key={item.item_id}
          className="flex flex-col gap-1 py-3 md:flex-row md:items-start md:justify-between md:gap-4"
          data-testid={`check-${item.item_id}`}
        >
          <div>
            <p className="text-body font-medium text-ink">
              <span className="mr-2 font-mono text-caption text-ink-muted">{item.item_id}</span>
              {item.title}
            </p>
            {item.action ? <p className="mt-1 text-small text-ink-muted">{item.action}</p> : null}
          </div>
          <Badge tone={tone[item.status] ?? "neutral"}>
            {checklistStatusLabel[item.status] ?? item.status}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
