"use client";

import { useParams } from "next/navigation";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Progress } from "@/components/ui/Progress";
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
  const todo = data.items.filter((i) => i.status === "missing" || i.status === "warning");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Case Strength"
        description="What is in your file and what is still missing. Readiness measures available information; it does not predict legal success."
      />

      <Card>
        <h2 className="text-h2 text-ink" data-testid="checklist-heading">
          {data.required_met} of {data.required_total} required items complete
        </h2>
        <div className="mt-3 max-w-xl">
          <Progress
            value={data.required_met}
            max={data.required_total}
            label="Required checklist items complete"
          />
        </div>
        <p className="mt-3 text-small text-ink-muted">
          {todo.length === 0
            ? "Nothing is missing from the checklist."
            : `${todo.length} ${todo.length === 1 ? "item needs" : "items need"} action. Each one says what to add.`}
        </p>
      </Card>
      <Card title="Required" description="Items the case cannot be put together without.">
        <ItemList items={required} />
      </Card>
      <Card title="Recommended" description="Items that make the file easier to review.">
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

const open = (status: string) => status === "missing" || status === "warning";

function ItemList({ items }: { items: ChecklistItem[] }) {
  const ordered = [...items].sort((a, b) => Number(open(b.status)) - Number(open(a.status)));
  return (
    <ul className="divide-y divide-rule">
      {ordered.map((item) => (
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
            {item.action && open(item.status) ? (
              <p className="mt-1 text-small text-ink-muted">
                <span className="font-medium text-ink">Next step:</span> {item.action}
              </p>
            ) : null}
          </div>
          <Badge tone={tone[item.status] ?? "neutral"}>
            {checklistStatusLabel[item.status] ?? item.status}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
