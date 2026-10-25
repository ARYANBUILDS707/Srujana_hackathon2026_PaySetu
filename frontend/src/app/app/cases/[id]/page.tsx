"use client";

import { useParams } from "next/navigation";
import { AmountSummary } from "@/components/cases/AmountSummary";
import { useCase } from "@/components/cases/CaseContext";
import { ClockTimeline } from "@/components/cases/ClockTimeline";
import { DayStrip } from "@/components/cases/DayStrip";
import { DeliveryDetails } from "@/components/cases/DeliveryDetails";
import { EvidencePackCard } from "@/components/cases/EvidencePackCard";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Disclosure } from "@/components/ui/Disclosure";
import { Notice } from "@/components/ui/Notice";
import { Progress } from "@/components/ui/Progress";
import { appCopy, clockGlossary, nextActionCopy } from "@/content/app";
import type { BuyerResponse } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function CaseOverviewPage() {
  const params = useParams<{ id: string }>();
  const { caseData } = useCase();
  const responses = useApiGet<BuyerResponse[]>(`/cases/${params.id}/responses`);
  const next = nextActionCopy(caseData.next_action, caseData.id);
  const summary = caseData.checklist_summary;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="flex flex-col gap-6 lg:col-span-2">
        <section
          aria-labelledby="next-action"
          className="rounded-lg border border-rule border-l-4 border-l-accent bg-surface p-4 md:p-6"
        >
          <p className="text-caption uppercase tracking-wide text-ink-muted">Next step</p>
          <h2 id="next-action" className="mt-1 text-h2 text-ink">
            {next.title}
          </h2>
          <p className="mt-1 max-w-2xl text-body text-ink-muted">{next.body}</p>
          <div className="mt-4">
            <ButtonLink href={next.href}>{next.cta}</ButtonLink>
          </div>
        </section>

        <Card
          title="Payment timeline (DeemedClock)"
          description="The 15 days the buyer has to object in writing, then the dates that follow. Each date is calculated by the PaySetu backend from the recorded facts."
        >
          <DayStrip caseData={caseData} responses={responses.data ?? []} />
          <Disclosure summary="What these terms mean">
            <dl className="flex flex-col gap-2">
              {clockGlossary.map((g) => (
                <div key={g.term}>
                  <dt className="font-medium text-ink">{g.term}</dt>
                  <dd className="text-ink-muted">{g.meaning}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-2 text-caption text-ink-muted">
              PaySetu&apos;s reading of the MSMED Act, pending review by an advocate.
            </p>
          </Disclosure>
          <div className="mt-6 border-t border-rule pt-6">
            <ClockTimeline caseData={caseData} responses={responses.data ?? []} />
          </div>
          {caseData.clock.terms_capped_at_45 ? (
            <div className="mt-4">
              <Notice tone="warning" title="Agreed terms capped at 45 days">
                The agreed period was longer than the 45-day maximum, so the due date uses 45 days.
              </Notice>
            </div>
          ) : null}
        </Card>

        <Card
          title="Delivery details"
          description="What was recorded when the delivery was logged."
        >
          <DeliveryDetails caseData={caseData} />
        </Card>

        <EvidencePackCard caseId={caseData.id} />
      </div>

      <div className="flex flex-col gap-6">
        <Card title="Amounts">
          <AmountSummary caseData={caseData} />
        </Card>

        <Card title="Case Strength">
          <p className="text-body text-ink" data-testid="checklist-summary">
            {summary.required_met} of {summary.required_total} required items complete
          </p>
          <div className="mt-2">
            <Progress
              value={summary.required_met}
              max={summary.required_total}
              label="Required checklist items complete"
            />
          </div>
          {summary.warnings > 0 ? (
            <p className="mt-2 text-small text-warning">
              {summary.warnings} {summary.warnings === 1 ? "item needs" : "items need"} attention
            </p>
          ) : null}
          <p className="mt-2 text-small text-ink-muted">
            Readiness measures available information; it does not predict legal success.
          </p>
          <div className="mt-3">
            <ButtonLink href={`/app/cases/${caseData.id}/checklist`} variant="secondary">
              Open checklist
            </ButtonLink>
          </div>
        </Card>

        <Notice tone="warning" title={appCopy.pendingReview.title}>
          <p>{appCopy.pendingReview.body}</p>
          <details className="mt-2">
            <summary className="w-fit cursor-pointer font-medium text-info hover:text-primary">
              Rules awaiting confirmation ({caseData.clock.unconfirmed_rules.length})
            </summary>
            <p className="mt-2 break-words font-mono text-caption">
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
