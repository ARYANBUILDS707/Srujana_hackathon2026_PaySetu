"use client";

import Link from "next/link";
import { CaseRows } from "@/components/cases/CaseRows";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { eligibilityLabel } from "@/content/app";
import type { CaseSummary, Supplier } from "@/lib/api/types";
import { formatMoney, sumMoney } from "@/lib/format";
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
  const objections = list.filter((c) => c.acceptance_state === "objection_raised").length;
  const overdue = list.filter((c) => c.payment_state === "overdue").length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description={`${supplier.data.legal_name}. Your deliveries, the payment dates the MSMED Act counts from, and what each case needs next.`}
        actions={<ButtonLink href="/app/cases/new">Record delivery</ButtonLink>}
      />

      {list.length === 0 && !cases.error ? (
        <EmptyState
          title="Record your first delivery"
          body="PaySetu keeps the invoice, the proof of delivery and the buyer's replies together, and shows the dates the payment clock runs from. Start with one delivery."
          action={<ButtonLink href="/app/cases/new">Record delivery</ButtonLink>}
        />
      ) : (
        <section
          aria-label="Financial overview"
          className="rounded-lg border border-rule bg-surface"
        >
          <dl className="grid divide-y divide-rule md:grid-cols-3 md:divide-x md:divide-y-0">
            <Stat
              label="Tracked invoice principal"
              value={formatMoney(sumMoney(list.map((c) => c.invoice_amount)), 2)}
              hint="Sum of invoice amounts across all cases"
            />
            <Stat
              label="Cases"
              value={String(list.length)}
              hint={`${windowOpen} with the objection window open`}
            />
            <Stat
              label="Needs attention"
              value={String(attention.length)}
              hint={`${overdue} overdue · ${objections} with an objection raised`}
            />
          </dl>
        </section>
      )}

      {list.length > 0 || cases.error ? (
        <Card
          title="What to do next"
          description="Overdue payments and open objections. Open a case to see its next step."
        >
          {cases.error ? (
            <ErrorState
              message={cases.error.message}
              requestId={cases.error.requestId}
              onRetry={cases.reload}
            />
          ) : attention.length === 0 ? (
            <p className="text-small text-ink-muted">Nothing needs attention today.</p>
          ) : (
            <>
              <ul className="mb-4 flex flex-col gap-1 text-small text-ink">
                {objections > 0 ? (
                  <li>
                    {objections} {objections === 1 ? "case has" : "cases have"} a written objection.
                    Record when it is removed to fix the acceptance date.
                  </li>
                ) : null}
                {overdue > 0 ? (
                  <li>
                    {overdue} {overdue === 1 ? "case is" : "cases are"} past the payment due date.
                    Check the evidence is complete before the buyer is contacted.
                  </li>
                ) : null}
              </ul>
              <CaseRows cases={attention} />
            </>
          )}
        </Card>
      ) : null}

      {list.length > 0 ? (
        <Card
          title="Recent cases"
          actions={
            <Link
              href="/app/cases"
              className="text-small font-medium text-info hover:text-primary hover:underline"
            >
              View all cases
            </Link>
          }
        >
          <CaseRows cases={list.slice(0, 5)} />
        </Card>
      ) : null}

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

      <Notice tone="warning" title="Pending legal review">
        Calculation rules are provisional until an advocate confirms them. Amounts are illustrative.
      </Notice>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="p-4 md:p-6">
      <dt className="text-small font-medium text-ink-muted">{label}</dt>
      <dd className="mt-1 whitespace-nowrap text-display tabular-nums text-ink">{value}</dd>
      <p className="mt-1 text-small text-ink-muted">{hint}</p>
    </div>
  );
}
