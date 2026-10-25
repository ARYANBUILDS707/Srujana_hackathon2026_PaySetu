"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { controlClass, Field } from "@/components/ui/Fields";
import { Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";
import { safeNext } from "@/lib/session/redirect";

const copy = authCopy.login;

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const reason = copy.reasons[params.get("reason") ?? ""];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api<Me>("/auth/login", { method: "POST", json: { email, password } });
      router.replace(next);
    } catch (e) {
      setError(asApiError(e));
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-rule bg-surface p-4 md:p-6">
      <h1 className="text-h1 text-ink">{copy.title}</h1>
      <p className="mt-1 text-body text-ink-muted">{copy.intro}</p>

      <form onSubmit={submit} className="mt-6 flex flex-col gap-4" noValidate>
        {reason && !error ? <Notice tone="info">{reason}</Notice> : null}
        {error ? (
          <Notice tone="danger" title="Could not sign in">
            {error.status === 429 || error.status === 401 || error.status === 0
              ? error.message
              : (error.fieldErrors[0]?.message ?? error.message)}
          </Notice>
        ) : null}
        <Field label="Email" required>
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
        <Field label="Password" required>
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="current-password"
              value={password}
              maxLength={128}
              onChange={(e) => setPassword(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Button type="submit" loading={busy} disabled={!email.trim() || !password}>
          {copy.submit}
        </Button>
        <Link
          href="/forgot-password"
          className="w-fit text-small font-medium text-info hover:text-primary hover:underline"
        >
          {authCopy.forgot.linkFromLogin}
        </Link>
      </form>

      <p className="mt-6 text-small text-ink-muted">
        {copy.switchPrompt}{" "}
        <Link
          href={`/signup${next !== "/app" ? `?next=${encodeURIComponent(next)}` : ""}`}
          className="font-medium text-info hover:text-primary hover:underline"
        >
          {copy.switchLink}
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
