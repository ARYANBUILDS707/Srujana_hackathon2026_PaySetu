"use client";

import { Progress } from "@/components/ui/Progress";
import { useCase } from "@/components/cases/CaseContext";
import { formatDate, formatMoney } from "@/lib/format";

/** Where the payment stands, at a glance. All values are as returned by the case API. */
export function CaseSummaryStrip() {
  const { caseData } = useCase();
  const { clock, amounts, checklist_summary: summary } = caseData;
  const items = [
    { label: "Delivered", value: formatDate(caseData.delivery_date) },
    { label: "Payment due", value: clock.due_date ? formatDate(clock.due_date) : "Not fixed yet" },
    { label: "Outstanding principal", value: formatMoney(amounts.outstanding_principal, 2) },
  ];
  return (
    <section
      aria-label="Case summary"
      className="grid divide-y divide-rule rounded-lg border border-rule bg-surface md:grid-cols-4 md:divide-x md:divide-y-0"
    >
      {items.map((item) => (
        <div key={item.label} className="p-4">
          <p className="text-small text-ink-muted">{item.label}</p>
          <p className="mt-1 whitespace-nowrap text-h3 tabular-nums text-ink">{item.value}</p>
        </div>
      ))}
      <div className="p-4">
        <p className="text-small text-ink-muted">Evidence readiness</p>
        <p className="mt-1 text-h3 tabular-nums text-ink">
          {summary.required_met} of {summary.required_total} required
        </p>
        <div className="mt-2">
          <Progress
            value={summary.required_met}
            max={summary.required_total}
            label="Required checklist items complete"
          />
        </div>
      </div>
    </section>
  );
}
