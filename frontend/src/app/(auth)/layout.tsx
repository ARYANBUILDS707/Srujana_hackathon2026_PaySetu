import { Wordmark } from "@/components/ui/Wordmark";
import type { ReactNode } from "react";
import { landingCopy } from "@/content/landing";

// Sign-in and sign-up share the landing page's header and footer.
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-rule bg-surface">
        <div className="mx-auto flex h-16 max-w-7xl items-center px-4 md:px-8">
          <Wordmark href="/" />
        </div>
      </header>
      <main className="flex flex-1 items-start justify-center bg-[radial-gradient(60%_50%_at_50%_0%,var(--color-peach),transparent)] px-4 py-10 md:py-16">
        <div className="w-full max-w-md">{children}</div>
      </main>
      <footer className="border-t border-rule bg-surface py-6">
        <p className="mx-auto max-w-7xl px-4 text-caption text-ink-muted md:px-8">
          {landingCopy.disclaimer}
        </p>
      </footer>
    </div>
  );
}
