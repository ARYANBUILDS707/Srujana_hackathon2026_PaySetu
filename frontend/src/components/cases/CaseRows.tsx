import Link from "next/link";
import type { CaseSummary } from "@/lib/api/types";
import { formatDate, formatMoney } from "@/lib/format";
import { AcceptanceBadge, PaymentBadge } from "./StatusBadges";

const link = "font-medium text-ink hover:text-primary hover:underline";

/**
 * Cases as a compact table on wide screens and as stacked rows on phones. Everything shown is
 * returned by the cases API; there is no "last updated" field in it, so none is shown.
 */
export function CaseRows({ cases }: { cases: CaseSummary[] }) {
  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-small">
          <thead>
            <tr className="border-b border-rule text-ink-muted">
              <th scope="col" className="py-2 pr-4 font-medium">
                Buyer
              </th>
              <th scope="col" className="py-2 pr-4 font-medium">
                Reference
              </th>
              <th scope="col" className="py-2 pr-4 text-right font-medium">
                Invoice amount
              </th>
              <th scope="col" className="py-2 pr-4 font-medium">
                Payment due
              </th>
              <th scope="col" className="py-2 font-medium">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {cases.map((c) => (
              <tr key={c.id} className="transition-colors duration-150 hover:bg-surface-subtle">
                <td className="max-w-64 py-3 pr-4">
                  <Link href={`/app/cases/${c.id}`} className={`${link} block truncate`}>
                    {c.buyer.legal_name}
                  </Link>
                  <span className="block truncate text-caption text-ink-muted">
                    Invoice {c.invoice_number}
                  </span>
                </td>
                <td className="whitespace-nowrap py-3 pr-4 font-mono text-caption text-ink-muted">
                  {c.reference}
                </td>
                <td className="whitespace-nowrap py-3 pr-4 text-right font-medium tabular-nums text-ink">
                  {formatMoney(c.invoice_amount)}
                </td>
                <td className="whitespace-nowrap py-3 pr-4 tabular-nums text-ink-muted">
                  {c.due_date ? formatDate(c.due_date) : "Not fixed yet"}
                </td>
                <td className="py-3">
                  <div className="flex flex-wrap gap-1">
                    <AcceptanceBadge state={c.acceptance_state} />
                    <PaymentBadge state={c.payment_state} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="divide-y divide-rule md:hidden">
        {cases.map((c) => (
          <li key={c.id} className="py-3">
            <Link href={`/app/cases/${c.id}`} className="flex flex-col gap-2">
              <span className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 truncate font-medium text-ink">{c.buyer.legal_name}</span>
                <span className="shrink-0 whitespace-nowrap font-medium tabular-nums text-ink">
                  {formatMoney(c.invoice_amount)}
                </span>
              </span>
              <span className="font-mono text-caption text-ink-muted">
                {c.reference} · Invoice {c.invoice_number}
              </span>
              <span className="flex flex-wrap gap-1">
                <AcceptanceBadge state={c.acceptance_state} />
                <PaymentBadge state={c.payment_state} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
