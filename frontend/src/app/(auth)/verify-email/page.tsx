"use client";

import { useEffect, useRef, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { LoadingBlock, Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { VerifyEmailResult } from "@/lib/api/types";

const copy = authCopy.verify;

type Stage =
  | { kind: "checking" }
  | { kind: "missing" }
  | { kind: "ready"; token: string }
  | { kind: "invalid" }
  | { kind: "done" };

/** Reads `#token=…` once and removes it from the address bar; kept only in memory. */
function takeTokenFromFragment(): string | null {
  const match = /(?:^#|&)token=([A-Za-z0-9_-]{1,128})/.exec(window.location.hash);
  window.history.replaceState(null, "", window.location.pathname);
  return match ? match[1] : null;
}

export default function VerifyEmailPage() {
  const [stage, setStage] = useState<Stage>({ kind: "checking" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  // Read once; React development mode runs effects twice, so reuse the first read.
  const taken = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (taken.current === undefined) taken.current = takeTokenFromFragment();
    const token = taken.current;
    setStage(token ? { kind: "ready", token } : { kind: "missing" });

    // Opening another emailed link in this same tab changes only the fragment (no reload).
    function onHashChange() {
      const next = takeTokenFromFragment();
      if (next) setStage({ kind: "ready", token: next });
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Confirmation needs a click: link scanners that open URLs cannot use up the token.
  async function confirm() {
    if (stage.kind !== "ready") return;
    setBusy(true);
    setError(null);
    try {
      await api<VerifyEmailResult>("/auth/verify-email", {
        method: "POST",
        json: { token: stage.token },
      });
      setStage({ kind: "done" });
    } catch (e) {
      const failure = asApiError(e);
      if (failure.code === "invalid_verification_token") setStage({ kind: "invalid" });
      else setError(failure);
    } finally {
      setBusy(false);
    }
  }

  const card = "rounded-lg border border-rule bg-surface p-4 md:p-6";

  if (stage.kind === "checking") return <LoadingBlock label={copy.checking} />;

  if (stage.kind === "missing" || stage.kind === "invalid") {
    const missing = stage.kind === "missing";
    return (
      <div className={card} data-testid="verify-unusable">
        <h1 className="text-h1 text-ink">{missing ? copy.missingTitle : copy.invalidTitle}</h1>
        <p className="mt-2 text-body text-ink-muted">
          {missing ? copy.missingBody : copy.invalidBody}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <ButtonLink href="/app">{copy.signInForNew}</ButtonLink>
        </div>
      </div>
    );
  }

  if (stage.kind === "done") {
    return (
      <div className={card} data-testid="verify-done">
        <h1 className="text-h1 text-ink">{copy.doneTitle}</h1>
        <div className="mt-4">
          <Notice tone="success">{copy.doneBody}</Notice>
        </div>
        <p className="mt-4 text-small text-ink-muted">{copy.scope}</p>
        <div className="mt-6">
          <ButtonLink href="/app">{copy.toWorkspace}</ButtonLink>
        </div>
      </div>
    );
  }

  return (
    <div className={card}>
      <h1 className="text-h1 text-ink">{copy.pageTitle}</h1>
      <p className="mt-1 text-body text-ink-muted">{copy.pageIntro}</p>
      {error ? (
        <div className="mt-4">
          <Notice tone="danger" title="Email not confirmed">
            {error.message}
          </Notice>
        </div>
      ) : null}
      <div className="mt-6">
        <Button onClick={confirm} loading={busy}>
          {copy.confirm}
        </Button>
      </div>
      <p className="mt-4 text-small text-ink-muted">{copy.scope}</p>
    </div>
  );
}
