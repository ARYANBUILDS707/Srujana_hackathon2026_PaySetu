"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AcceptanceBadge, PaymentBadge } from "@/components/cases/StatusBadges";
import { CaseProvider, useCase } from "@/components/cases/CaseContext";
import { CaseSummaryStrip } from "@/components/cases/CaseSummaryStrip";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { appCopy } from "@/content/app";
import { formatDate, formatMoney } from "@/lib/format";

function CaseHeader() {
  const { caseData } = useCase();
  const pathname = usePathname();
  const base = `/app/cases/${caseData.id}`;

  return (
    <>
      <header className="mb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="break-words text-h1 text-ink">
              {caseData.reference} · {caseData.buyer.legal_name}
            </h1>
            <p className="mt-1 text-body text-ink-muted">
              Invoice {caseData.invoice_number} ·{" "}
              <span className="font-medium tabular-nums text-ink">
                {formatMoney(caseData.invoice_amount, 2)}
              </span>{" "}
              · delivered {formatDate(caseData.delivery_date)}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge tone="warning">Demo data</Badge>
              <AcceptanceBadge state={caseData.acceptance_state} />
              <PaymentBadge state={caseData.payment_state} />
            </div>
          </div>
          <ButtonLink href={`${base}#evidence-pack`} variant="secondary">
            <Icon name="download" className="size-4" />
            Evidence pack
          </ButtonLink>
        </div>
      </header>
      <div className="mb-6">
        <CaseSummaryStrip />
      </div>
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
                  className={`block border-b-2 px-4 py-3 text-small font-medium transition-colors duration-150 ${
                    active
                      ? "border-brass text-ink"
                      : "border-transparent text-ink-muted hover:border-rule-strong hover:text-ink"
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
