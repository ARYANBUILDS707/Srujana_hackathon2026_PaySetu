import Link from "next/link";
import type { CaseSummary } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";
import { AcceptanceBadge, PaymentBadge } from "./StatusBadges";

export function CaseRows({ cases }: { cases: CaseSummary[] }) {
  return (
    <ul className="divide-y divide-rule">
      {cases.map((c) => (
        <li key={c.id}>
          <Link
            href={`/app/cases/${c.id}`}
            className="flex flex-col gap-2 py-3 hover:bg-canvas md:flex-row md:items-center md:justify-between md:gap-4 md:px-2"
          >
            <div className="min-w-0">
              <p className="truncate text-body font-medium text-ink">
                {c.reference} · {c.buyer.legal_name}
              </p>
              <p className="text-small text-ink-muted">
                Invoice {c.invoice_number} · {formatMoney(c.invoice_amount)} · delivered{" "}
                {formatDate(c.delivery_date)}
                {c.due_date ? ` · due ${formatDate(c.due_date)}` : ""}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <AcceptanceBadge state={c.acceptance_state} />
              <PaymentBadge state={c.payment_state} />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
