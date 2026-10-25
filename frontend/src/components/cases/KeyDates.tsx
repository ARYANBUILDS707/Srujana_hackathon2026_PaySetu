import type { CaseDetail } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

interface Row {
  label: string;
  value: string | null;
  field: string;
  emptyReason: string;
}

/** Legal dates with a "Why this date?" explanation from the rule engine (DESIGN.md 5.7). */
export function KeyDates({ caseData }: { caseData: CaseDetail }) {
  const { clock } = caseData;
  const rows: Row[] = [
    { label: "Delivered", value: caseData.delivery_date, field: "", emptyReason: "" },
    { label: "Last day to object", value: clock.window_end, field: "window_end", emptyReason: "" },
    {
      label: "Acceptance date",
      value: clock.acceptance_date,
      field: "acceptance_date",
      emptyReason: "Not fixed yet",
    },
    {
      label: "Payment due",
      value: clock.due_date,
      field: "due_date",
      emptyReason: "Not fixed yet",
    },
    {
      label: "Interest from",
      value: clock.interest_start,
      field: "interest_start",
      emptyReason: "Not fixed yet",
    },
    {
      label: "Indicative limitation",
      value: clock.indicative_limitation_date,
      field: "indicative_limitation_date",
      emptyReason: "Not fixed yet",
    },
  ];

  return (
    <dl className="divide-y divide-rule">
      {rows.map((row) => {
        const explanations = clock.explanations.filter((e) => e.field === row.field && row.field);
        return (
          <div key={row.label} className="py-3">
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-small text-ink-muted">{row.label}</dt>
              <dd className="text-body font-medium tabular-nums text-ink">
                {row.value ? formatDate(row.value) : row.emptyReason}
              </dd>
            </div>
            {explanations.length > 0 ? (
              <details className="mt-1">
                <summary className="w-fit cursor-pointer text-small text-primary hover:text-primary-hover">
                  Why this date?
                </summary>
                <div className="mt-2 rounded-md bg-primary-tint p-3 text-small text-ink">
                  {explanations.map((e) => (
                    <p key={e.text}>{e.text}</p>
                  ))}
                  <p className="mt-2 text-caption text-ink-muted">
                    PaySetu&apos;s reading of the rules {explanations[0].rule_ids.join(", ")}.
                    Confirm with counsel.
                  </p>
                </div>
              </details>
            ) : null}
          </div>
        );
      })}
    </dl>
  );
}
