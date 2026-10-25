"use client";

import Link from "next/link";
import { CaseRows } from "@/components/cases/CaseRows";
import { AcceptanceBadge, PaymentBadge } from "@/components/cases/StatusBadges";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState, LoadingBlock, Notice, Skeleton } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { Progress } from "@/components/ui/Progress";
import { eligibilityLabel, nextActionCopy } from "@/content/app";
import { onboardingStatusLabel, onboardingStatusTone } from "@/content/onboarding";
import type { CaseDetail, CaseSummary, Onboarding, Supplier } from "@/lib/api/types";
import { daysBetween, formatDate, formatMoney, sumMoney, todayInIndia } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

const UPCOMING_DAYS = 30;

/** Most urgent first: overdue (earliest due), objection raised, then the nearest due date. */
function urgency(c: CaseSummary): [number, string] {
  const rank =
    c.payment_state === "overdue"
      ? 0
      : c.acceptance_state === "objection_raised"
        ? 1
        : c.payment_state === "settled"
          ? 4
          : c.due_date
            ? 2
            : 3;
  return [rank, c.due_date ?? c.delivery_date];
}

function byUrgency(a: CaseSummary, b: CaseSummary): number {
  const [ra, da] = urgency(a);
  const [rb, db] = urgency(b);
  return ra - rb || da.localeCompare(db);
}

function relativeDays(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

export default function DashboardPage() {
  const supplier = useApiGet<Supplier>("/supplier");
  const cases = useApiGet<CaseSummary[]>("/cases?limit=100");
  const onboarding = useApiGet<Onboarding>("/onboarding");

  const list = cases.data ?? [];
  const ranked = [...list].sort(byUrgency);
  const focus = ranked.find((c) => c.payment_state !== "settled") ?? null;
  const focusDetail = useApiGet<CaseDetail>(focus ? `/cases/${focus.id}` : null);

  if (supplier.error)
    return (
      <ErrorState
        message={supplier.error.message}
        requestId={supplier.error.requestId}
        onRetry={supplier.reload}
      />
    );
  if (!supplier.data || (cases.loading && !cases.data))
    return <LoadingBlock label="Loading dashboard" />;

  const today = todayInIndia();
  const attention = ranked.filter(
    (c) => c.acceptance_state === "objection_raised" || c.payment_state === "overdue",
  );
  const upcoming = ranked
    .filter((c) => c.due_date && c.payment_state === "not_due")
    .map((c) => ({ c, days: daysBetween(today, c.due_date as string) }))
    .filter(({ days }) => days >= 0)
    .sort((a, b) => a.days - b.days);
  const dueSoon = upcoming.filter(({ days }) => days <= UPCOMING_DAYS).length;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description={`${supplier.data.legal_name}. Your deliveries, the payment dates the MSMED Act counts from, and what each case needs next.`}
        actions={
          // Secondary here: the recommended next step below is the page's one primary action.
          <ButtonLink href="/app/cases/new" variant="secondary">
            Record delivery
          </ButtonLink>
        }
      />

      {cases.error ? (
        <ErrorState
          message={cases.error.message}
          requestId={cases.error.requestId}
          onRetry={cases.reload}
        />
      ) : list.length === 0 ? (
        <EmptyState
          title="Record your first delivery"
          body="PaySetu keeps the invoice, the proof of delivery and the buyer's replies together, and shows the dates the payment clock runs from. Start with one delivery."
          action={<ButtonLink href="/app/cases/new">Record delivery</ButtonLink>}
        />
      ) : (
        <>
          {focus ? <NextStep focus={focus} detail={focusDetail.data} /> : null}

          <section
            aria-label="Overview"
            className="grid divide-y divide-rule rounded-lg border border-rule bg-surface shadow-card md:grid-cols-3 md:divide-x md:divide-y-0"
          >
            <Stat
              label="Tracked invoice principal"
              value={formatMoney(sumMoney(list.map((c) => c.invoice_amount)), 2)}
              hint={`Across ${list.length} ${list.length === 1 ? "case" : "cases"}`}
            />
            <Stat
              label="Cases needing attention"
              value={String(attention.length)}
              hint="Overdue, or a written objection is open"
            />
            <Stat
              label={`Payments due in ${UPCOMING_DAYS} days`}
              value={String(dueSoon)}
              hint="From the dates PaySetu worked out"
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-3">
              <Card
                title="Needs attention"
                description="Overdue payments and open objections, most urgent first."
              >
                {attention.length === 0 ? (
                  <p className="text-small text-ink-muted">Nothing needs attention today.</p>
                ) : (
                  <CaseRows cases={attention} />
                )}
              </Card>
              <Card
                title="Recent cases"
                actions={
                  <Link
                    href="/app/cases"
                    className="text-small font-medium text-accent-strong hover:underline"
                  >
                    View all cases
                  </Link>
                }
              >
                <CaseRows cases={list.slice(0, 5)} />
              </Card>
            </div>
            <div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
              <Card title="Upcoming deadlines" description="Payment due dates still ahead.">
                {upcoming.length === 0 ? (
                  <p className="text-small text-ink-muted">No payment due dates ahead.</p>
                ) : (
                  <ul className="divide-y divide-rule">
                    {upcoming.slice(0, 5).map(({ c, days }) => (
                      <li key={c.id}>
                        <Link
                          href={`/app/cases/${c.id}`}
                          className="flex items-center justify-between gap-3 py-2.5 hover:text-accent-strong"
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-body font-medium text-ink">
                              {c.buyer.legal_name}
                            </span>
                            <span className="font-mono text-caption text-ink-muted">
                              {c.reference}
                            </span>
                          </span>
                          <span className="shrink-0 text-right">
                            <span className="block text-small font-medium tabular-nums text-ink">
                              {formatDate(c.due_date)}
                            </span>
                            <span className="text-caption text-ink-muted">
                              {relativeDays(days)}
                            </span>
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <BusinessCard onboarding={onboarding.data} />
              <EligibilityCard supplier={supplier.data} />
            </div>
          </div>
        </>
      )}

      <Notice tone="warning" title="Pending legal review">
        Calculation rules are provisional until an advocate confirms them. Amounts are illustrative.
      </Notice>
    </div>
  );
}

function NextStep({ focus, detail }: { focus: CaseSummary; detail: CaseDetail | null }) {
  if (!detail)
    return (
      <div className="rounded-lg border border-rule bg-surface p-6">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="mt-3 h-8 w-2/3" />
      </div>
    );
  const next = nextActionCopy(detail.next_action, detail.id);
  const summary = detail.checklist_summary;
  return (
    <section
      aria-labelledby="next-step-heading"
      className="grid gap-6 rounded-lg border border-rule bg-surface p-5 shadow-card md:grid-cols-3 md:p-6"
      data-testid="dashboard-next-step"
    >
      <div className="min-w-0 md:col-span-2">
        <p className="flex items-center gap-2 text-small font-medium text-accent-strong">
          <span aria-hidden="true" className="size-2 rounded-full bg-accent" />
          Recommended next step
        </p>
        <h2 id="next-step-heading" className="mt-2 text-h2 text-ink">
          {next.title}
        </h2>
        <p className="mt-1 max-w-xl text-body text-ink-muted">{next.body}</p>
        <p className="mt-3 flex flex-wrap items-center gap-2 text-small text-ink-muted">
          <span className="min-w-0 break-words">
            <span className="font-mono">{focus.reference}</span> · {focus.buyer.legal_name}
          </span>
          <AcceptanceBadge state={focus.acceptance_state} />
          <PaymentBadge state={focus.payment_state} />
        </p>
        <div className="mt-5">
          <ButtonLink href={next.href}>{next.cta}</ButtonLink>
        </div>
      </div>
      <div className="rounded-md bg-surface-subtle p-4">
        <p className="text-small text-ink-muted">Evidence readiness for this case</p>
        <p className="mt-1 text-h2 tabular-nums text-ink">
          {summary.required_met} of {summary.required_total}
        </p>
        <p className="text-small text-ink-muted">required items in the file</p>
        <div className="mt-3">
          <Progress
            value={summary.required_met}
            max={summary.required_total}
            label="Required checklist items complete"
          />
        </div>
        <Link
          href={`/app/cases/${detail.id}/checklist`}
          className="mt-3 inline-block text-small font-medium text-accent-strong hover:underline"
        >
          See what is missing
        </Link>
      </div>
    </section>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="p-4 md:p-6">
      <p className="text-small font-medium text-ink-muted">{label}</p>
      <p className="mt-1 whitespace-nowrap text-display tabular-nums text-ink">{value}</p>
      <p className="mt-1 text-small text-ink-muted">{hint}</p>
    </div>
  );
}

function BusinessCard({ onboarding }: { onboarding: Onboarding | null }) {
  return (
    <Card title="Business profile" description="Self-declared details and your Udyam certificate.">
      {onboarding ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Badge tone={onboardingStatusTone[onboarding.status]}>
            {onboardingStatusLabel[onboarding.status]}
          </Badge>
          <Link
            href="/app/onboarding"
            className="text-small font-medium text-accent-strong hover:underline"
          >
            {onboarding.status === "NOT_STARTED"
              ? "Start business profile"
              : "Open business profile"}
          </Link>
        </div>
      ) : (
        <Skeleton className="h-6 w-32" />
      )}
    </Card>
  );
}

function EligibilityCard({ supplier }: { supplier: Supplier }) {
  return (
    <Card
      title="Supplier eligibility"
      description="What the recorded profile shows. This is not a legal determination."
      actions={
        <Badge
          tone={
            supplier.eligibility_verdict === "eligible"
              ? "success"
              : supplier.eligibility_verdict === "not_eligible"
                ? "danger"
                : "warning"
          }
        >
          {eligibilityLabel[supplier.eligibility_verdict] ?? supplier.eligibility_verdict}
        </Badge>
      }
    >
      <ul className="divide-y divide-rule">
        {supplier.eligibility_reasons.map((reason) => (
          <li key={reason.code} className="flex items-start justify-between gap-4 py-2 text-small">
            <span className="text-ink">{reason.message}</span>
            <Badge tone={reason.status === "met" ? "success" : "warning"}>
              {reason.status === "met" ? "Met" : "Check"}
            </Badge>
          </li>
        ))}
      </ul>
    </Card>
  );
}
