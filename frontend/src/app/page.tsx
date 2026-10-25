import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Wordmark } from "@/components/ui/Wordmark";
import { landingCopy as copy } from "@/content/landing";

// Landing page (DESIGN.md Section 12.1). Every figure shown is labelled sample content.

// Mirrors the rules engine for a delivery with no written objection and no written terms:
// deemed acceptance is the delivery day; payment is due by Day 15; interest from Day 16.
const sampleTimeline = [
  { label: "Delivered", date: "01 Oct 2026", note: "Recorded fact", state: "done" },
  {
    label: "Deemed accepted",
    date: "01 Oct 2026",
    note: "No written objection within 15 days, so the delivery day counts",
    state: "done",
  },
  { label: "Objection window closed", date: "16 Oct 2026", note: "Day 15", state: "done" },
  { label: "Payment due", date: "16 Oct 2026", note: "No written payment terms", state: "next" },
  { label: "Interest starts", date: "17 Oct 2026", note: "If still unpaid", state: "later" },
] as const;

function SampleTag() {
  return <Badge tone="warning">{copy.previewLabel}</Badge>;
}

function ProductPreview() {
  return (
    <figure
      aria-label="Sample case workspace"
      className="overflow-hidden rounded-lg border border-rule bg-surface shadow-float"
    >
      <div className="flex items-center justify-between gap-3 border-b border-rule bg-surface-subtle px-4 py-3">
        <div className="flex items-center gap-1.5" aria-hidden="true">
          <span className="size-2.5 rounded-full bg-rule-strong" />
          <span className="size-2.5 rounded-full bg-rule-strong" />
          <span className="size-2.5 rounded-full bg-rule-strong" />
        </div>
        <SampleTag />
      </div>
      <div className="grid gap-6 p-5 md:grid-cols-5 md:p-6">
        <div className="md:col-span-3">
          <p className="font-mono text-caption text-ink-muted">
            PS-0000-0000 · Sample Buyer Pvt Ltd
          </p>
          <p className="mt-3 text-small text-ink-muted">Payment timeline</p>
          <ol className="mt-3 border-l border-rule-strong pl-5">
            {sampleTimeline.map((m) => (
              <li key={m.label} className="relative pb-4 last:pb-0">
                <span
                  aria-hidden="true"
                  className={`absolute -left-[26px] top-1.5 size-2.5 rounded-full border-2 ${
                    m.state === "done"
                      ? "border-primary bg-primary"
                      : m.state === "next"
                        ? "border-accent bg-accent"
                        : "border-rule-strong bg-surface"
                  }`}
                />
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className="text-body font-medium text-ink">{m.label}</p>
                  <p className="text-small tabular-nums text-ink">{m.date}</p>
                </div>
                <p className="text-caption text-ink-muted">{m.note}</p>
              </li>
            ))}
          </ol>
        </div>
        <div className="flex flex-col gap-4 md:col-span-2">
          <div className="rounded-md bg-peach p-4">
            <p className="text-small text-ink-muted">Invoice amount</p>
            <p className="mt-1 text-display tabular-nums text-ink">Rs 5,00,000</p>
            <p className="mt-1 text-caption text-ink-muted">
              Illustrative interest shown separately
            </p>
          </div>
          <div className="rounded-md border border-rule p-4">
            <p className="text-small text-ink-muted">Evidence readiness</p>
            <ul className="mt-2 space-y-1.5 text-small">
              {[
                ["Invoice", true],
                ["Signed challan", true],
                ["Written payment terms", false],
              ].map(([label, ok]) => (
                <li key={String(label)} className="flex items-center gap-2 text-ink">
                  <span
                    aria-hidden="true"
                    className={`flex size-4 items-center justify-center rounded-full ${ok ? "bg-success text-on-status" : "border border-rule-strong"}`}
                  >
                    {ok ? <Icon name="check" className="size-3" /> : null}
                  </span>
                  {label}
                  <span className="sr-only">{ok ? "(present)" : "(missing)"}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <figcaption className="border-t border-rule px-5 py-3 text-caption text-ink-muted md:px-6">
        {copy.previewNote}
      </figcaption>
    </figure>
  );
}

function BentoTile({
  title,
  question,
  body,
  className = "",
  children,
}: {
  title: string;
  question: string;
  body: string;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <article
      className={`flex flex-col rounded-lg border border-rule bg-surface p-5 shadow-card md:p-6 ${className}`}
    >
      <p className="text-small font-medium text-accent-strong">{title}</p>
      <h3 className="mt-1 text-h2 text-ink">{question}</h3>
      <p className="mt-2 text-body text-ink-muted">{body}</p>
      {children ? <div className="mt-5 flex-1">{children}</div> : null}
    </article>
  );
}

function ClockIllustration() {
  // Days 0 to 15 of the objection window (sample): which days have passed.
  return (
    <div aria-label="Sample 15-day objection window" role="img">
      <div className="flex gap-1">
        {Array.from({ length: 16 }, (_, day) => (
          <span
            key={day}
            className={`h-8 flex-1 rounded-sm ${day <= 9 ? "bg-strip" : day === 10 ? "bg-accent" : "bg-surface-hover"}`}
          />
        ))}
      </div>
      <div className="mt-2 flex justify-between text-caption text-ink-muted">
        <span>Delivery · Day 0</span>
        <span>Day 10 today</span>
        <span>Day 15 · last day to object</span>
      </div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-surface">
      <header className="sticky top-0 z-20 border-b border-rule bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 md:px-8">
          <Wordmark href="/" />
          <nav aria-label="Primary" className="flex items-center gap-1 md:gap-2">
            <Link
              href="/login"
              className="rounded-md px-3 py-2 text-small font-medium text-ink hover:bg-surface-subtle"
            >
              {copy.signIn}
            </Link>
            <ButtonLink href="/signup" className="hidden sm:inline-flex">
              {copy.createAccount}
            </ButtonLink>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="bg-[radial-gradient(70%_60%_at_50%_0%,var(--color-peach),transparent)]">
          <div className="mx-auto max-w-6xl px-4 pb-16 pt-14 md:px-8 md:pt-20 lg:pb-24">
            <div className="mx-auto max-w-4xl text-center">
              <h1 className="mx-auto max-w-4xl text-[2.25rem] font-bold leading-[1.1] tracking-tight text-ink sm:text-5xl lg:text-[3.5rem]">
                <span className="block">
                  {copy.headlineLead}{" "}
                  <span className="text-accent-display">{copy.headlineAccent}</span>
                </span>
                <span className="block">{copy.headlineTail}</span>
              </h1>
              <div className="mt-10 flex flex-wrap justify-center gap-3">
                <ButtonLink href="/app">{copy.openDemo}</ButtonLink>
                <ButtonLink href="#how-it-works" variant="secondary">
                  {copy.seeHow}
                </ButtonLink>
              </div>
            </div>
            <div className="mx-auto mt-12 max-w-4xl lg:mt-16">
              <ProductPreview />
            </div>
          </div>
        </section>

        <section
          id="how-it-works"
          aria-labelledby="steps-heading"
          className="scroll-mt-16 border-y border-rule bg-canvas"
        >
          <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 lg:py-20">
            <h2 id="steps-heading" className="text-[1.75rem] font-bold tracking-tight text-ink">
              {copy.stepsHeading}
            </h2>
            <p className="mt-2 max-w-xl text-body text-ink-muted">{copy.stepsIntro}</p>
            <ol className="mt-10 grid gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-5">
              {copy.steps.map((step, index) => (
                <li key={step.title} className="relative">
                  <span className="flex size-9 items-center justify-center rounded-full border border-rule-strong bg-surface font-mono text-small font-semibold text-ink">
                    {index + 1}
                  </span>
                  <h3 className="mt-4 text-h3 text-ink">{step.title}</h3>
                  <p className="mt-1.5 text-small text-ink-muted">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="features" aria-labelledby="features-heading" className="scroll-mt-16">
          <div className="mx-auto max-w-6xl px-4 py-16 md:px-8 lg:py-20">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2
                  id="features-heading"
                  className="text-[1.75rem] font-bold tracking-tight text-ink"
                >
                  {copy.featuresHeading}
                </h2>
                <p className="mt-2 max-w-xl text-body text-ink-muted">{copy.featuresIntro}</p>
              </div>
              <SampleTag />
            </div>
            <div className="mt-10 grid gap-4 lg:grid-cols-6">
              <BentoTile {...copy.features.clock} className="lg:col-span-4">
                <ClockIllustration />
              </BentoTile>
              <BentoTile {...copy.features.vault} className="lg:col-span-2">
                <ul className="divide-y divide-rule rounded-md border border-rule text-small">
                  {[
                    ["invoice-118.pdf", "9f2c41ab…e07d"],
                    ["challan-signed.jpg", "4be19c02…a31f"],
                  ].map(([name, hash]) => (
                    <li key={name} className="flex items-center justify-between gap-3 px-3 py-2">
                      <span className="truncate text-ink">{name}</span>
                      <span className="shrink-0 font-mono text-caption text-ink-muted">{hash}</span>
                    </li>
                  ))}
                </ul>
              </BentoTile>
              <BentoTile {...copy.features.strength} className="lg:col-span-2">
                <ul className="space-y-1.5 text-small">
                  <li className="flex justify-between gap-2">
                    <span className="text-ink">Invoice uploaded</span>
                    <Badge tone="success">Met</Badge>
                  </li>
                  <li className="flex justify-between gap-2">
                    <span className="text-ink">Proof of delivery</span>
                    <Badge tone="warning">Missing</Badge>
                  </li>
                </ul>
              </BentoTile>
              <BentoTile {...copy.features.interest} className="lg:col-span-2">
                <div className="rounded-md bg-peach p-3">
                  <p className="text-caption text-ink-muted">Illustrative interest, sample</p>
                  <p className="mt-0.5 text-h2 tabular-nums text-ink">Rs 1,181.51</p>
                  <p className="text-caption text-ink-muted">3 × bank rate, monthly rests</p>
                </div>
              </BentoTile>
              <BentoTile {...copy.features.pack} className="lg:col-span-2">
                <ul className="space-y-1 font-mono text-caption text-ink-muted">
                  <li>01_case_summary.md</li>
                  <li>03_timeline.md</li>
                  <li>evidence/01_invoice_9f2c41ab.pdf</li>
                  <li>manifest.json</li>
                </ul>
              </BentoTile>
            </div>
          </div>
        </section>

        <section aria-labelledby="not-heading" className="border-t border-rule bg-canvas">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 md:grid-cols-2 md:px-8">
            <div>
              <h2 id="not-heading" className="text-h2 text-ink">
                {copy.notHeading}
              </h2>
              <p className="mt-3 text-body text-ink-muted">{copy.notBody}</p>
            </div>
            <div>
              <h2 className="text-h2 text-ink">{copy.honestHeading}</h2>
              <ul className="mt-3 space-y-3">
                {copy.honest.map((line) => (
                  <li key={line} className="flex gap-3 text-body text-ink-muted">
                    <span
                      aria-hidden="true"
                      className="mt-2.5 size-1.5 shrink-0 rounded-full bg-accent"
                    />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-rule bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 md:flex-row md:items-center md:justify-between md:px-8">
          <Wordmark href="/" />
          <p className="text-caption text-ink-muted">{copy.disclaimer}</p>
          <nav aria-label="Footer" className="flex gap-4 text-small">
            <Link href="/login" className="text-ink-muted hover:text-ink">
              {copy.signIn}
            </Link>
            <Link href="/signup" className="text-ink-muted hover:text-ink">
              {copy.createAccount}
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
