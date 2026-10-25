import { Badge } from "@/components/ui/Badge";
import { Notice } from "@/components/ui/Notice";
import { appCopy } from "@/content/app";
import type { CaseDetail } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";

const statusMessage: Record<string, string> = {
  not_applicable: "Interest cannot be worked out until the acceptance date is fixed.",
  not_yet_due: "Interest has not started yet.",
  rate_data_unavailable:
    "No recorded bank rate covers this period, so PaySetu does not calculate interest.",
};

/** Amounts as returned by the interest engine. Nothing is calculated in the browser. */
export function AmountSummary({ caseData }: { caseData: CaseDetail }) {
  const { amounts } = caseData;
  const computed = amounts.interest_status === "computed";
  return (
    <div>
      <dl className="divide-y divide-rule">
        <Row label="Invoice amount" value={formatMoney(amounts.principal, 2)} />
        <Row label="Paid so far" value={formatMoney(amounts.paid, 2)} />
        <Row label="Outstanding principal" value={formatMoney(amounts.outstanding_principal, 2)} />
        <Row
          label={`Interest to ${formatDate(amounts.as_of)}`}
          value={computed ? formatMoney(amounts.interest, 2) : "Not calculated"}
          badge={<Badge>Illustrative</Badge>}
        />
        <Row
          label="Total claimable (illustrative)"
          value={computed ? formatMoney(amounts.total_claimable, 2) : "Not calculated"}
          strong
        />
      </dl>
      {!computed ? (
        <p className="mt-3 text-small text-ink-muted">
          {statusMessage[amounts.interest_status] ?? "Interest was not calculated."}
        </p>
      ) : null}
      {amounts.uses_unverified_rates ? (
        <div className="mt-3">
          <Notice tone="warning" title="Unverified bank rate">
            {appCopy.unverifiedRate}
          </Notice>
        </div>
      ) : null}
    </div>
  );
}

function Row({
  label,
  value,
  badge,
  strong,
}: {
  label: string;
  value: string;
  badge?: React.ReactNode;
  strong?: boolean;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-4 py-3 ${strong ? "border-t-2 border-rule" : ""}`}
    >
      <dt className="flex items-center gap-2 text-small text-ink-muted">
        {label}
        {badge}
      </dt>
      <dd
        className={`shrink-0 whitespace-nowrap tabular-nums text-ink ${strong ? "text-h3" : "text-body font-medium"}`}
      >
        {value}
      </dd>
    </div>
  );
}
