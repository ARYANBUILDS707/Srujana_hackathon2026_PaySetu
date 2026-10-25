"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { useCase } from "@/components/cases/CaseContext";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { controlClass, Field } from "@/components/ui/Fields";
import { ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { appCopy } from "@/content/app";
import type { Interest } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function InterestPage() {
  const params = useParams<{ id: string }>();
  const { caseData } = useCase();
  const [asOf, setAsOf] = useState("");
  const query = asOf ? `?as_of=${asOf}` : "";
  const { data, error, loading, reload } = useApiGet<Interest>(
    `/cases/${params.id}/interest${query}`,
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Interest"
        description="An illustrative interest figure from the backend interest engine. It is not a demand, and no Buyer Cost Page or simulator exists in this build."
      />
      <Card
        title="Interest calculator"
        description="Illustrative interest under MSMED Act s.16, worked out by PaySetu's interest engine from the recorded bank rates."
        actions={<Badge tone="warning">Illustrative</Badge>}
      >
        <div className="max-w-xs">
          <Field label="Calculate as of" hint="Leave empty for today.">
            {(control) => (
              <input
                {...control}
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                className={controlClass}
              />
            )}
          </Field>
        </div>
      </Card>

      {error ? (
        <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />
      ) : loading || !data ? (
        <LoadingBlock label="Calculating interest" />
      ) : (
        <>
          <Card title="Result" actions={<Badge tone="warning">Illustrative</Badge>}>
            <dl className="divide-y divide-rule">
              <Row label="Calculated as of" value={formatDate(data.as_of)} />
              <Row
                label="Payment due"
                value={caseData.due_date ? formatDate(caseData.due_date) : "Not fixed yet"}
              />
              <Row
                label="Interest starts"
                value={data.interest_start ? formatDate(data.interest_start) : "Not fixed yet"}
              />
              <Row label="Principal" value={formatMoney(data.principal, 2)} />
              <Row
                label="Interest accrued (illustrative)"
                value={
                  data.status === "computed"
                    ? formatMoney(data.interest_accrued, 2)
                    : "Not calculated"
                }
                testId="interest-accrued"
              />
              <Row
                label="Total outstanding (illustrative)"
                value={
                  data.status === "computed"
                    ? formatMoney(data.total_outstanding, 2)
                    : "Not calculated"
                }
                strong
              />
            </dl>
            <p className="mt-3 text-small text-ink-muted" data-testid="interest-message">
              {data.message}
            </p>
          </Card>

          {data.uses_unverified_rates ? (
            <Notice tone="warning" title="Unverified bank rate">
              {appCopy.unverifiedRate}
            </Notice>
          ) : null}

          {data.periods.length > 0 ? (
            <Card
              title="Rate assumptions and workings"
              description="One row per monthly rest. Interest is capitalised at each rest. A rate marked Unverified has not been checked against an RBI notification."
            >
              <div className="overflow-x-auto">
                <table className="w-full min-w-160 text-left text-small">
                  <thead>
                    <tr className="bg-surface-sunken text-ink-muted">
                      <th scope="col" className="px-3 py-2 font-medium">
                        Period
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Days
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Rate (3× bank rate)
                      </th>
                      <th scope="col" className="px-3 py-2 text-right font-medium">
                        Opening balance
                      </th>
                      <th scope="col" className="px-3 py-2 text-right font-medium">
                        Interest
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule tabular-nums">
                    {data.periods.map((p) => (
                      <tr key={p.start}>
                        <td className="px-3 py-2">
                          {formatDate(p.start)} – {formatDate(p.end)}
                        </td>
                        <td className="px-3 py-2">{p.days}</td>
                        <td className="px-3 py-2">
                          {p.annual_rate_percent}%{" "}
                          {!p.rate_verified ? <Badge tone="warning">Unverified</Badge> : null}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {formatMoney(p.opening_balance, 2)}
                        </td>
                        <td className="px-3 py-2 text-right">{formatMoney(p.interest, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : null}

          <Notice tone="warning" title={appCopy.pendingReview.title}>
            Method assumptions are provisional until reviewed by an advocate:{" "}
            {data.unconfirmed_rules.join(", ") || "none"}. Open questions:{" "}
            {data.pending_reviews.join(", ")}.
          </Notice>
        </>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  strong,
  testId,
}: {
  label: string;
  value: string;
  strong?: boolean;
  testId?: string;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-4 py-3 ${strong ? "border-t-2 border-rule" : ""}`}
    >
      <dt className="text-small text-ink-muted">{label}</dt>
      <dd
        data-testid={testId}
        className={`whitespace-nowrap tabular-nums text-ink ${strong ? "text-display" : "text-body font-medium"}`}
      >
        {value}
      </dd>
    </div>
  );
}
