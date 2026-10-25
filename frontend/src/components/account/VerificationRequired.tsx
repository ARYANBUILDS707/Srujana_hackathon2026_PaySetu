"use client";

import { useState } from "react";
import { ResendVerification } from "@/components/account/ResendVerification";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { useSession } from "@/lib/session/SessionContext";

const copy = authCopy.verify;

/**
 * Shown instead of the case workspace until the email is confirmed (Phase 7A). This is UX:
 * the API refuses every workspace request with 403 `email_not_verified` regardless.
 */
export function VerificationRequired() {
  const { me, refresh } = useSession();
  const [checking, setChecking] = useState(false);
  const [stillPending, setStillPending] = useState(false);

  async function check() {
    setChecking(true);
    try {
      const current = await refresh();
      setStillPending(!current.user.email_verified);
    } finally {
      setChecking(false);
    }
  }

  return (
    <section
      aria-labelledby="verify-heading"
      className="max-w-2xl rounded-lg border border-rule border-l-4 border-l-brass bg-surface p-4 md:p-6"
      data-testid="verification-required"
    >
      <h1 id="verify-heading" className="text-h1 text-ink">
        {copy.requiredTitle}
      </h1>
      <p className="mt-2 text-body text-ink-muted">
        {copy.requiredIntro} <strong className="break-all text-ink">{me.user.email}</strong>.
      </p>
      <ol className="mt-4 list-decimal space-y-1 pl-5 text-body text-ink">
        {copy.requiredSteps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="mt-4 text-small text-ink-muted">{copy.scope}</p>
      <div className="mt-6 flex flex-col gap-4">
        <div>
          <Button onClick={check} loading={checking}>
            {copy.continue}
          </Button>
        </div>
        {stillPending ? <Notice tone="warning">{copy.stillUnverified}</Notice> : null}
        <ResendVerification onAlreadyVerified={() => void refresh()} />
      </div>
    </section>
  );
}
