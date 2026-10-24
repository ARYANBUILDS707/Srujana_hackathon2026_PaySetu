import { landingCopy as copy } from "@/content/landing";

// Landing page (DESIGN.md Section 12.1). Sign-up and log-in are shown but disabled until
// authentication ships (Phase 3 / Phase 7); they must not link to routes that do not exist yet.
export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <main className="mx-auto w-full max-w-180 flex-1 px-4 py-12 md:px-6 lg:px-8 lg:py-16">
        <p className="text-h3 text-primary">{copy.productName}</p>
        <h1 className="mt-4 text-display text-ink">{copy.tagline}</h1>
        <p className="mt-4 text-body text-ink-muted">{copy.intro}</p>

        <div className="mt-8 flex flex-col gap-3 md:flex-row">
          <span
            role="link"
            aria-disabled="true"
            aria-describedby="accounts-unavailable"
            className="inline-flex h-11 min-w-22 cursor-not-allowed items-center justify-center rounded-sm bg-primary px-4 font-medium text-white opacity-40"
          >
            {copy.signUp}
          </span>
          <span
            role="link"
            aria-disabled="true"
            aria-describedby="accounts-unavailable"
            className="inline-flex h-11 min-w-22 cursor-not-allowed items-center justify-center rounded-sm border border-rule-strong bg-surface px-4 font-medium text-ink opacity-40"
          >
            {copy.logIn}
          </span>
        </div>
        <p id="accounts-unavailable" className="mt-2 text-small text-ink-muted">
          {copy.accountsUnavailable}
        </p>

        <section aria-labelledby="steps-heading" className="mt-12">
          <h2 id="steps-heading" className="text-h2 text-ink">
            {copy.stepsHeading}
          </h2>
          <ol className="mt-4 divide-y divide-rule border-y border-rule">
            {copy.steps.map((step, index) => (
              <li key={step.title} className="flex gap-4 py-4">
                <span className="font-mono text-small text-ink-muted tabular-nums">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="text-h3 text-ink">{step.title}</h3>
                  <p className="mt-1 text-body text-ink-muted">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section
          aria-labelledby="not-heading"
          className="mt-12 rounded-md border-l-3 border-info bg-info-tint p-4"
        >
          <h2 id="not-heading" className="text-h3 text-ink">
            {copy.notHeading}
          </h2>
          <p className="mt-2 text-body text-ink">{copy.notBody}</p>
        </section>
      </main>

      <footer className="border-t border-rule px-4 py-6 md:px-6 lg:px-8">
        <p className="mx-auto max-w-180 text-caption text-ink-muted">{copy.disclaimer}</p>
      </footer>
    </div>
  );
}
