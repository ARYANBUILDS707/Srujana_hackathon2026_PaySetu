"use client";

import { useParams } from "next/navigation";
import { AmountSummary } from "@/components/cases/AmountSummary";
import { useCase } from "@/components/cases/CaseContext";
import { DayStrip } from "@/components/cases/DayStrip";
import { EvidencePackCard } from "@/components/cases/EvidencePackCard";
import { KeyDates } from "@/components/cases/KeyDates";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Notice } from "@/components/ui/Notice";
import { appCopy, nextActionCopy } from "@/content/app";
import type { BuyerResponse } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function CaseOverviewPage() {
  const params = useParams<{ id: string }>();
  const { caseData } = useCase();
  const responses = useApiGet<BuyerResponse[]>(`/cases/${params.id}/responses`);
  const next = nextActionCopy(caseData.next_action, caseData.id);
  const summary = caseData.checklist_summary;

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="flex flex-col gap-6 lg:col-span-3">
        <section
          aria-labelledby="next-action"
          className="rounded-lg border border-primary bg-primary-tint p-5"
        >
          <p className="text-caption text-primary-hover">Next step</p>
          <h2 id="next-action" className="mt-1 text-h2 text-ink">
            {next.title}
          </h2>
          <p className="mt-1 text-small text-ink">{next.body}</p>
          <div className="mt-4">
            <ButtonLink href={next.href}>{next.cta}</ButtonLink>
          </div>
        </section>

        <Card title="DeemedClock" description="The 15 days the buyer has to object in writing.">
          <DayStrip caseData={caseData} responses={responses.data ?? []} />
        </Card>

        <Card title="Key dates">
          <KeyDates caseData={caseData} />
          {caseData.clock.terms_capped_at_45 ? (
            <div className="mt-3">
              <Notice tone="warning" title="Agreed terms capped at 45 days">
                The agreed period was longer than the 45-day maximum, so the due date uses 45 days.
              </Notice>
            </div>
          ) : null}
        </Card>
      </div>

      <div className="flex flex-col gap-6 lg:col-span-2">
        <Card title="Amounts">
          <AmountSummary caseData={caseData} />
        </Card>

        <Card title="Case Strength">
          <p className="text-body text-ink" data-testid="checklist-summary">
            {summary.required_met} of {summary.required_total} required items complete
          </p>
          {summary.warnings > 0 ? (
            <p className="mt-1 text-small text-warning">
              {summary.warnings} {summary.warnings === 1 ? "item needs" : "items need"} attention
            </p>
          ) : null}
          <p className="mt-2 text-small text-ink-muted">
            A readiness list only. It does not predict any outcome.
          </p>
          <div className="mt-3">
            <ButtonLink href={`/app/cases/${caseData.id}/checklist`} variant="secondary">
              Open checklist
            </ButtonLink>
          </div>
        </Card>

        <EvidencePackCard caseId={caseData.id} />

        <Notice tone="warning" title={appCopy.pendingReview.title}>
          <p>{appCopy.pendingReview.body}</p>
          <details className="mt-2">
            <summary className="w-fit cursor-pointer font-medium text-primary hover:text-primary-hover">
              Rules awaiting confirmation ({caseData.clock.unconfirmed_rules.length})
            </summary>
            <p className="mt-2 font-mono text-caption">
              {caseData.clock.unconfirmed_rules.join(", ")}
            </p>
            <p className="mt-2 text-caption text-ink-muted">
              Open questions for an advocate: {caseData.clock.pending_reviews.join(", ")}
            </p>
          </details>
        </Notice>
      </div>
    </div>
  );
}
