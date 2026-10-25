import { Badge } from "@/components/ui/Badge";
import type { CaseDetail } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";

const dealLabel: Record<string, string> = {
  written: "Written agreement",
  verbal: "Verbal or no written terms",
};

/** The recorded facts of the delivery, exactly as entered. */
export function DeliveryDetails({ caseData }: { caseData: CaseDetail }) {
  const rows: [string, string][] = [
    ["Buyer", caseData.buyer.legal_name],
    ["Buyer GSTIN", caseData.buyer.gstin ?? "Not recorded"],
    ["Invoice number", caseData.invoice_number],
    ["Invoice date", formatDate(caseData.invoice_date)],
    ["Invoice amount", formatMoney(caseData.invoice_amount, 2)],
    ["Delivery date", formatDate(caseData.delivery_date)],
    ["Delivery location", caseData.delivery_location ?? "Not recorded"],
    ["Payment terms", dealLabel[caseData.deal_type] ?? caseData.deal_type],
  ];
  if (caseData.agreed_payment_days !== null)
    rows.push(["Agreed payment period", `${caseData.agreed_payment_days} days`]);
  return (
    <div>
      <dl className="grid gap-x-8 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div
            key={label}
            className="flex items-baseline justify-between gap-4 border-b border-rule py-2.5"
          >
            <dt className="shrink-0 text-small text-ink-muted">{label}</dt>
            <dd className="min-w-0 break-words text-right text-body font-medium text-ink">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {caseData.description ? (
        <p className="mt-3 text-small text-ink-muted">
          <Badge>Description</Badge> {caseData.description}
        </p>
      ) : null}
    </div>
  );
}
