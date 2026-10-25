"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AcceptanceBadge, PaymentBadge } from "@/components/cases/StatusBadges";
import { CaseProvider, useCase } from "@/components/cases/CaseContext";
import { Badge } from "@/components/ui/Badge";
import { appCopy } from "@/content/app";
import { formatDate, formatMoney } from "@/lib/format";

function CaseHeader() {
  const { caseData } = useCase();
  const pathname = usePathname();
  const base = `/app/cases/${caseData.id}`;

  return (
    <>
      <header className="mb-6">
        <Link
          href="/app/cases"
          className="text-small font-medium text-primary hover:text-primary-hover"
        >
          ← All cases
        </Link>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-h1 text-ink">
              {caseData.reference} · {caseData.buyer.legal_name}
            </h1>
            <p className="mt-1 text-small text-ink-muted">
              Invoice {caseData.invoice_number} · {formatMoney(caseData.invoice_amount, 2)} ·
              delivered {formatDate(caseData.delivery_date)}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="warning">Demo data</Badge>
            <AcceptanceBadge state={caseData.acceptance_state} />
            <PaymentBadge state={caseData.payment_state} />
          </div>
        </div>
      </header>
      <nav aria-label="Case sections" className="mb-6 overflow-x-auto border-b border-rule">
        <ul className="flex min-w-max gap-1">
          {appCopy.caseTabs.map((tab) => {
            const href = tab.slug ? `${base}/${tab.slug}` : base;
            const active = pathname === href;
            return (
              <li key={tab.label}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`block border-b-2 px-4 py-3 text-small font-medium ${
                    active
                      ? "border-primary text-primary"
                      : "border-transparent text-ink-muted hover:text-ink"
                  }`}
                >
                  {tab.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}

export default function CaseLayout({ children }: { children: ReactNode }) {
  const params = useParams<{ id: string }>();
  return (
    <CaseProvider caseId={params.id}>
      <CaseHeader />
      {children}
    </CaseProvider>
  );
}
