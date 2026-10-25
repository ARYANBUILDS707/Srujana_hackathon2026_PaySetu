"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError } from "@/lib/api/client";
import type { ResendVerificationResult } from "@/lib/api/types";

const copy = authCopy.verify;

/** "Send a new link" with the server's cooldown shown as a countdown. */
export function ResendVerification({ onAlreadyVerified }: { onAlreadyVerified: () => void }) {
  const [busy, setBusy] = useState(false);
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [result, setResult] = useState<"sent" | "failed" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const remaining = Math.max(0, Math.ceil((until - now) / 1000));
  useEffect(() => {
    if (until <= Date.now()) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [until]);

  async function resend() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await api<ResendVerificationResult>("/auth/resend-verification", {
        method: "POST",
      });
      setResult(response.notification);
      setNow(Date.now());
      setUntil(Date.now() + response.retry_after_seconds * 1000);
    } catch (e) {
      const failure = asApiError(e);
      if (failure.code === "already_verified") {
        onAlreadyVerified();
        return;
      }
      if (failure.retryAfterSeconds) {
        setNow(Date.now());
        setUntil(Date.now() + failure.retryAfterSeconds * 1000);
      }
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <Button variant="secondary" onClick={resend} loading={busy} disabled={remaining > 0}>
          {remaining > 0 ? copy.resendIn(remaining) : copy.resend}
        </Button>
      </div>
      <div aria-live="polite">
        {result === "sent" ? <Notice tone="success">{copy.sent}</Notice> : null}
        {result === "failed" ? <Notice tone="danger">{copy.failed}</Notice> : null}
        {error ? <Notice tone="danger">{error}</Notice> : null}
      </div>
    </div>
  );
}
