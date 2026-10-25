"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { controlClass, Field } from "@/components/ui/Fields";
import { Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { ForgotPasswordResult } from "@/lib/api/types";

const copy = authCopy.forgot;

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  // The server answers the same way whether or not the account exists.
  const [done, setDone] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<ForgotPasswordResult>("/auth/forgot-password", {
        method: "POST",
        json: { email },
      });
      setDone(result.detail);
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-rule bg-surface p-4 md:p-6">
      <h1 className="text-h1 text-ink">{done ? copy.doneTitle : copy.title}</h1>
      {done ? (
        <div className="mt-4" data-testid="forgot-done">
          <Notice tone="info">{done}</Notice>
        </div>
      ) : (
        <>
          <p className="mt-1 text-body text-ink-muted">{copy.intro}</p>
          <form onSubmit={submit} className="mt-6 flex flex-col gap-4" noValidate>
            {error && error.fieldErrors.length === 0 ? (
              <Notice tone="danger" title="Could not send the link">
                {error.message}
              </Notice>
            ) : null}
            <Field label="Email" required error={error?.forField("email")}>
              {(control) => (
                <input
                  {...control}
                  type="email"
                  autoComplete="email"
                  value={email}
                  maxLength={254}
                  onChange={(e) => setEmail(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
            <Button type="submit" loading={busy} disabled={!email.trim()}>
              {copy.submit}
            </Button>
          </form>
        </>
      )}
      <p className="mt-6 text-small">
        <Link href="/login" className="font-medium text-info hover:text-primary hover:underline">
          {copy.back}
        </Link>
      </p>
    </div>
  );
}
