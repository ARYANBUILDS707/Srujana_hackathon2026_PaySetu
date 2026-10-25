"use client";

import Link from "next/link";
import { CaseRows } from "@/components/cases/CaseRows";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { eligibilityLabel } from "@/content/app";
import type { CaseSummary, Supplier } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function DashboardPage() {
  const supplier = useApiGet<Supplier>("/supplier");
  const cases = useApiGet<CaseSummary[]>("/cases?limit=100");

  if (supplier.error)
    return (
      <ErrorState
        message={
          supplier.error.code === "profile_incomplete"
            ? "The demo supplier has not been created yet. Run `make seed` in the project folder, then reload."
            : supplier.error.message
        }
        requestId={supplier.error.requestId}
        onRetry={supplier.reload}
      />
    );
  if (!supplier.data || (cases.loading && !cases.data))
    return <LoadingBlock label="Loading dashboard" />;

  const list = cases.data ?? [];
  const attention = list.filter(
    (c) => c.acceptance_state === "objection_raised" || c.payment_state === "overdue",
  );
  const windowOpen = list.filter((c) => c.acceptance_state === "window_open").length;
  const overdue = list.filter((c) => c.payment_state === "overdue").length;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h1 text-ink">Dashboard</h1>
          <p className="mt-1 text-small text-ink-muted">{supplier.data.legal_name}</p>
        </div>
        <ButtonLink href="/app/cases/new">Log a delivery</ButtonLink>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Cases" value={list.length} />
        <Stat label="Objection window open" value={windowOpen} />
        <Stat label="Payment overdue" value={overdue} />
      </div>

      <Card title="Needs attention" description="Overdue payments and open objections.">
        {cases.error ? (
          <ErrorState
            message={cases.error.message}
            requestId={cases.error.requestId}
            onRetry={cases.reload}
          />
        ) : attention.length === 0 ? (
          <p className="text-small text-ink-muted">Nothing needs attention today.</p>
        ) : (
          <CaseRows cases={attention} />
        )}
      </Card>

      <Card
        title="Supplier eligibility"
        description="What the recorded profile shows. This is not a legal determination."
        actions={
          <Badge
            tone={
              supplier.data.eligibility_verdict === "eligible"
                ? "success"
                : supplier.data.eligibility_verdict === "not_eligible"
                  ? "danger"
                  : "warning"
            }
          >
            {eligibilityLabel[supplier.data.eligibility_verdict] ??
              supplier.data.eligibility_verdict}
          </Badge>
        }
      >
        <ul className="divide-y divide-rule">
          {supplier.data.eligibility_reasons.map((reason) => (
            <li
              key={reason.code}
              className="flex items-start justify-between gap-4 py-2 text-small"
            >
              <span className="text-ink">{reason.message}</span>
              <Badge tone={reason.status === "met" ? "success" : "warning"}>
                {reason.status === "met" ? "Met" : "Check"}
              </Badge>
            </li>
          ))}
        </ul>
      </Card>

      {list.length === 0 && !cases.error ? (
        <EmptyState
          title="No deliveries yet"
          body="Log your first delivery to start the 15-day objection window and see the dates the MSMED Act counts from."
          action={<ButtonLink href="/app/cases/new">Log a delivery</ButtonLink>}
        />
      ) : (
        <Card
          title="Recent cases"
          actions={
            <Link
              href="/app/cases"
              className="text-small font-medium text-primary hover:text-primary-hover"
            >
              View all
            </Link>
          }
        >
          <CaseRows cases={list.slice(0, 5)} />
        </Card>
      )}
      <Notice tone="warning" title="Pending legal review">
        Calculation rules are provisional until an advocate confirms them. Amounts are illustrative.
      </Notice>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-5">
      <p className="text-small text-ink-muted">{label}</p>
      <p className="mt-1 text-display tabular-nums text-ink">{value}</p>
    </div>
  );
}
