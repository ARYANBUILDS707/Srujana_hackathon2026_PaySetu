"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { controlClass, Field } from "@/components/ui/Fields";
import { LoadingBlock, Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { PasswordUpdated } from "@/lib/api/types";

const copy = authCopy.reset;
const MIN_PASSWORD = 10;

type Stage =
  | { kind: "checking" }
  | { kind: "missing" }
  | { kind: "form"; token: string }
  | { kind: "invalid" }
  | { kind: "done"; notification: PasswordUpdated["notification"] };

/** Reads `#token=…` once, then removes it from the address bar. The token lives only in
 * this component's memory: never in storage, never in a URL the app requests. */
function takeTokenFromFragment(): string | null {
  const match = /(?:^#|&)token=([A-Za-z0-9_-]{1,128})/.exec(window.location.hash);
  window.history.replaceState(null, "", window.location.pathname);
  return match ? match[1] : null;
}

export default function ResetPasswordPage() {
  const [stage, setStage] = useState<Stage>({ kind: "checking" });
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  // The fragment is read once and then cleared, so a second effect run (React development
  // mode runs effects twice) must reuse the value instead of reading the cleared URL.
  const taken = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (taken.current === undefined) taken.current = takeTokenFromFragment();
    const token = taken.current;
    // Runs after hydration: the fragment is only readable in the browser.
    setStage(token ? { kind: "form", token } : { kind: "missing" });
  }, []);

  const mismatch = confirm.length > 0 && confirm !== password;
  const shortPassword = password.length > 0 && password.length < MIN_PASSWORD;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (stage.kind !== "form") return;
    setBusy(true);
    setError(null);
    try {
      const result = await api<PasswordUpdated>("/auth/reset-password", {
        method: "POST",
        json: { token: stage.token, new_password: password },
      });
      setPassword("");
      setConfirm("");
      setStage({ kind: "done", notification: result.notification });
    } catch (e) {
      const failure = asApiError(e);
      if (failure.code === "invalid_reset_token") setStage({ kind: "invalid" });
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
      <div className={card} data-testid="reset-unusable">
        <h1 className="text-h1 text-ink">{missing ? copy.missingTitle : copy.invalidTitle}</h1>
        <p className="mt-2 text-body text-ink-muted">
          {missing ? copy.missingBody : copy.invalidBody}
        </p>
        <div className="mt-6">
          <ButtonLink href="/forgot-password">{copy.requestNew}</ButtonLink>
        </div>
      </div>
    );
  }

  if (stage.kind === "done") {
    return (
      <div className={card} data-testid="reset-done">
        <h1 className="text-h1 text-ink">{copy.doneTitle}</h1>
        <div className="mt-4">
          <Notice tone="success" title={copy.doneBody}>
            {stage.notification === "sent" ? copy.noticeSent : copy.noticeFailed}
          </Notice>
        </div>
        <div className="mt-6">
          <ButtonLink href="/login?reason=password-reset">{copy.signIn}</ButtonLink>
        </div>
      </div>
    );
  }

  return (
    <div className={card}>
      <h1 className="text-h1 text-ink">{copy.title}</h1>
      <p className="mt-1 text-body text-ink-muted">{copy.intro}</p>
      <form onSubmit={submit} className="mt-6 flex flex-col gap-4" noValidate>
        {error && error.fieldErrors.length === 0 ? (
          <Notice tone="danger" title="Password not changed">
            {error.message}
          </Notice>
        ) : null}
        <Field
          label="New password"
          required
          hint={authCopy.signup.passwordHint}
          error={
            error?.forField("new_password") ??
            (shortPassword ? `Use at least ${MIN_PASSWORD} characters.` : undefined)
          }
        >
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="new-password"
              value={password}
              maxLength={128}
              onChange={(e) => setPassword(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field label={copy.confirmLabel} required error={mismatch ? copy.mismatch : undefined}>
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="new-password"
              value={confirm}
              maxLength={128}
              onChange={(e) => setConfirm(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Button
          type="submit"
          loading={busy}
          disabled={password.length < MIN_PASSWORD || confirm !== password}
        >
          {copy.submit}
        </Button>
      </form>
      <p className="mt-6 text-small">
        <Link href="/login" className="font-medium text-info hover:text-primary hover:underline">
          {authCopy.forgot.back}
        </Link>
      </p>
    </div>
  );
}
