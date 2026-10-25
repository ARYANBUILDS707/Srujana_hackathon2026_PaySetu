import { ButtonLink } from "@/components/ui/Button";
import { landingCopy as copy } from "@/content/landing";

// Landing page (DESIGN.md Section 12.1).
export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-rule bg-surface">
        <div className="mx-auto flex h-14 max-w-5xl items-center px-4 md:px-6">
          <span className="text-h3 font-semibold text-primary">{copy.productName}</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 md:px-6 lg:py-16">
        <div className="max-w-2xl">
          <h1 className="text-display text-ink">{copy.tagline}</h1>
          <p className="mt-4 text-body text-ink-muted">{copy.intro}</p>
          <div className="mt-8">
            <ButtonLink href="/app">{copy.openDemo}</ButtonLink>
          </div>
          <p className="mt-3 text-small text-ink-muted">{copy.demoNote}</p>
        </div>

        <section aria-labelledby="steps-heading" className="mt-14">
          <h2 id="steps-heading" className="text-h2 text-ink">
            {copy.stepsHeading}
          </h2>
          <ol className="mt-4 grid gap-4 md:grid-cols-3">
            {copy.steps.map((step, index) => (
              <li key={step.title} className="rounded-lg border border-rule bg-surface p-5">
                <span className="flex size-8 items-center justify-center rounded-full bg-primary-tint font-mono text-small text-primary">
                  {index + 1}
                </span>
                <h3 className="mt-3 text-h3 text-ink">{step.title}</h3>
                <p className="mt-1 text-small text-ink-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section
          aria-labelledby="not-heading"
          className="mt-10 rounded-lg border-l-4 border-primary bg-primary-tint p-5"
        >
          <h2 id="not-heading" className="text-h3 text-ink">
            {copy.notHeading}
          </h2>
          <p className="mt-2 text-body text-ink">{copy.notBody}</p>
        </section>
      </main>

      <footer className="border-t border-rule bg-surface px-4 py-6 md:px-6">
        <p className="mx-auto max-w-5xl text-caption text-ink-muted">{copy.disclaimer}</p>
      </footer>
    </div>
  );
}
