import { Badge, type Tone } from "@/components/ui/Badge";
import { Disclosure } from "@/components/ui/Disclosure";
import { responseKindLabel } from "@/content/app";
import type { BuyerResponse, CaseDetail } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

type Kind = "fact" | "calculated" | "pending";

interface Milestone {
  key: string;
  label: string;
  date: string | null;
  kind: Kind;
  detail?: string;
  field?: string; // key into clock.explanations
}

const kindBadge: Record<Kind, { label: string; tone: Tone }> = {
  fact: { label: "Recorded fact", tone: "neutral" },
  calculated: { label: "Calculated by PaySetu", tone: "primary" },
  pending: { label: "Pending", tone: "warning" },
};

/**
 * The DeemedClock as a chronological timeline. Every milestone comes from the case, its
 * recorded buyer responses or the backend clock; dates the clock has not fixed are shown as
 * pending, never guessed. No legal rule is evaluated in the browser.
 */
export function ClockTimeline({
  caseData,
  responses,
}: {
  caseData: CaseDetail;
  responses: BuyerResponse[];
}) {
  const { clock } = caseData;

  const dated: Milestone[] = [
    { key: "delivery", label: "Delivery recorded", date: caseData.delivery_date, kind: "fact" },
    {
      key: "window_end",
      label: "Last day for the buyer to object in writing",
      date: clock.window_end,
      kind: "calculated",
      field: "window_end",
    },
  ];
  for (const r of responses) {
    const label =
      r.kind === "objection"
        ? "Buyer objection recorded"
        : r.kind === "acknowledgement"
          ? "Buyer acknowledgement recorded"
          : `${responseKindLabel[r.kind]} recorded`;
    dated.push({
      key: `resp-${r.id}`,
      label,
      date: r.received_on,
      kind: "fact",
      detail: r.note,
    });
    if (r.objection_removed_on) {
      dated.push({
        key: `rem-${r.id}`,
        label: "Objection marked as removed",
        date: r.objection_removed_on,
        kind: "fact",
      });
    }
  }
  if (clock.acceptance_date)
    dated.push({
      key: "acceptance",
      label: "Acceptance date",
      date: clock.acceptance_date,
      kind: "calculated",
      field: "acceptance_date",
    });
  if (clock.due_date)
    dated.push({
      key: "due",
      label: "Payment due",
      date: clock.due_date,
      kind: "calculated",
      field: "due_date",
    });
  if (clock.interest_start)
    dated.push({
      key: "interest",
      label: "Interest starts",
      date: clock.interest_start,
      kind: "calculated",
      field: "interest_start",
    });
  if (clock.indicative_limitation_date)
    dated.push({
      key: "limitation",
      label: "Indicative limitation date",
      date: clock.indicative_limitation_date,
      kind: "calculated",
      field: "indicative_limitation_date",
    });
  dated.sort((a, b) => (a.date as string).localeCompare(b.date as string));

  const pending: Milestone[] = [];
  if (!clock.acceptance_date)
    pending.push({
      key: "p-acceptance",
      label: "Acceptance date",
      date: null,
      kind: "pending",
      detail:
        clock.acceptance_state === "objection_raised"
          ? "Not fixed while a written objection is open."
          : "Not fixed yet.",
    });
  if (!clock.due_date)
    pending.push({
      key: "p-due",
      label: "Payment due",
      date: null,
      kind: "pending",
      detail: "Follows the acceptance date.",
    });
  if (!clock.interest_start)
    pending.push({
      key: "p-interest",
      label: "Interest starts",
      date: null,
      kind: "pending",
      detail: "Follows the payment due date.",
    });

  return (
    <ol aria-label="DeemedClock timeline" className="border-l border-rule-strong pl-6">
      {[...dated, ...pending].map((m) => {
        const explanations = m.field ? clock.explanations.filter((e) => e.field === m.field) : [];
        const unconfirmed = explanations
          .flatMap((e) => e.rule_ids)
          .filter((id) => clock.unconfirmed_rules.includes(id));
        const badge = kindBadge[m.kind];
        return (
          <li key={m.key} className="relative pb-6 last:pb-0">
            <span
              aria-hidden="true"
              className={`absolute -left-[31px] top-1 size-3 rounded-full border-2 ${
                m.kind === "pending"
                  ? "border-warning bg-surface"
                  : m.kind === "fact"
                    ? "border-primary bg-primary"
                    : "border-primary bg-surface"
              }`}
            />
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <p className="text-body font-medium text-ink">{m.label}</p>
              <p className="whitespace-nowrap text-body font-medium tabular-nums text-ink">
                {m.date ? formatDate(m.date) : "Not fixed yet"}
              </p>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <Badge tone={badge.tone}>{badge.label}</Badge>
              {unconfirmed.length > 0 ? (
                <Badge tone="warning">Legal assumption: not yet reviewed</Badge>
              ) : null}
            </div>
            {m.detail ? <p className="mt-1 text-small text-ink-muted">{m.detail}</p> : null}
            {explanations.length > 0 ? (
              <Disclosure summary="Why this date?">
                {explanations.map((e) => (
                  <p key={e.text}>{e.text}</p>
                ))}
                <p className="mt-2 text-caption text-ink-muted">
                  PaySetu&apos;s reading of the rules {explanations[0].rule_ids.join(", ")}.
                  {unconfirmed.length > 0
                    ? ` Not yet confirmed by an advocate: ${unconfirmed.join(", ")}.`
                    : ""}{" "}
                  Confirm with counsel.
                </p>
              </Disclosure>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
