import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { landingCopy as copy } from "@/content/landing";

// Landing page (DESIGN.md Section 12.1). The preview is labelled sample content, not data.
const sampleMilestones = [
  { label: "Delivery recorded", date: "01 Oct 2026", kind: "Recorded fact" },
  { label: "Last day to object in writing", date: "16 Oct 2026", kind: "Calculated date" },
  { label: "Payment due", date: "Not fixed yet", kind: "Pending" },
] as const;

function SamplePreview() {
  return (
    <figure
      aria-label="Sample case workspace"
      className="rounded-lg border border-rule bg-surface p-4 md:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Badge tone="warning">{copy.previewLabel}</Badge>
        <span className="font-mono text-caption text-ink-muted">PS-0000-0000</span>
      </div>
      <p className="mt-4 text-small text-ink-muted">Invoice amount</p>
      <p className="text-display tabular-nums text-ink">Rs 5,00,000.00</p>
      <ol className="mt-5 border-l border-rule-strong pl-5">
        {sampleMilestones.map((m) => (
          <li key={m.label} className="relative pb-5 last:pb-0">
            <span
              aria-hidden="true"
              className="absolute -left-[26px] top-1.5 size-2.5 rounded-full border-2 border-primary bg-surface"
            />
            <p className="text-body font-medium text-ink">{m.label}</p>
            <p className="text-small tabular-nums text-ink-muted">
              {m.date} · {m.kind}
            </p>
          </li>
        ))}
      </ol>
      <figcaption className="mt-5 border-t border-rule pt-3 text-caption text-ink-muted">
        {copy.previewNote}
      </figcaption>
    </figure>
  );
}

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-rule bg-surface">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-8">
          <span className="flex items-center gap-2 text-h3 font-semibold text-primary">
            <span
              aria-hidden="true"
              className="flex size-7 items-center justify-center rounded-md bg-primary text-small text-white"
            >
              P
            </span>
            {copy.productName}
          </span>
          <nav aria-label="Account" className="flex items-center gap-4">
            <a
              href="#how-it-works"
              className="hidden text-small font-medium text-ink-muted hover:text-ink md:inline"
            >
              How it works
            </a>
            <Link href="/login" className="text-small font-medium text-ink-muted hover:text-ink">
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-12 md:px-8 lg:grid-cols-2 lg:py-20">
          <div className="max-w-xl">
            <span aria-hidden="true" className="block h-1 w-10 rounded-full bg-brass" />
            <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight text-ink">
              {copy.headline}
            </h1>
            <p className="mt-4 text-h3 font-normal text-ink-muted">{copy.subheading}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/app">{copy.openDemo}</ButtonLink>
              <ButtonLink href="#how-it-works" variant="secondary">
                {copy.seeHow}
              </ButtonLink>
            </div>
            <p className="mt-4 text-small text-ink-muted">{copy.demoNote}</p>
          </div>
          <SamplePreview />
        </section>

        <section
          id="how-it-works"
          aria-labelledby="steps-heading"
          className="border-y border-rule bg-surface"
        >
          <div className="mx-auto max-w-7xl px-4 py-12 md:px-8 lg:py-16">
            <h2 id="steps-heading" className="text-h2 text-ink">
              {copy.stepsHeading}
            </h2>
            <p className="mt-1 max-w-xl text-body text-ink-muted">{copy.stepsIntro}</p>
            <ol className="mt-8 grid gap-x-8 gap-y-6 md:grid-cols-2 lg:grid-cols-5">
              {copy.steps.map((step, index) => (
                <li key={step.title} className="border-t-2 border-primary pt-4">
                  <span className="font-mono text-small text-ink-muted">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3 className="mt-1 text-h3 text-ink">{step.title}</h3>
                  <p className="mt-2 text-small text-ink-muted">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section
          aria-labelledby="not-heading"
          className="mx-auto max-w-7xl px-4 py-12 md:px-8 lg:py-16"
        >
          <div className="max-w-2xl rounded-lg border border-rule bg-surface-subtle p-5 md:p-6">
            <h2 id="not-heading" className="text-h3 text-ink">
              {copy.notHeading}
            </h2>
            <p className="mt-2 text-body text-ink-muted">{copy.notBody}</p>
          </div>
        </section>
      </main>

      <footer className="border-t border-rule bg-surface py-6">
        <p className="mx-auto max-w-7xl px-4 text-caption text-ink-muted md:px-8">
          {copy.disclaimer}
        </p>
      </footer>
    </div>
  );
}
