"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { controlClass, Field } from "@/components/ui/Fields";
import { Notice } from "@/components/ui/Notice";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { Me, SignupBody } from "@/lib/api/types";
import { safeNext } from "@/lib/session/redirect";

const copy = authCopy.signup;
const MIN_PASSWORD = 10;

function SignupForm() {
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));

  const [form, setForm] = useState({ fullName: "", businessName: "", email: "", password: "" });
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  // Early, friendly hint only; the server applies the full policy.
  const shortPassword = form.password.length > 0 && form.password.length < MIN_PASSWORD;
  const fieldError = (name: string) => error?.forField(name);
  const formLevelError = error && error.fieldErrors.length === 0 ? error.message : null;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const body: SignupBody = {
      full_name: form.fullName,
      business_name: form.businessName,
      email: form.email,
      password: form.password,
      accept_terms_version: copy.termsVersion,
    };
    try {
      await api<Me>("/auth/signup", { method: "POST", json: body });
      router.replace(next);
    } catch (e) {
      setError(asApiError(e));
      setBusy(false);
    }
  }

  const ready =
    form.fullName.trim() &&
    form.businessName.trim() &&
    form.email.trim() &&
    form.password.length >= MIN_PASSWORD &&
    accepted;

  return (
    <div className="rounded-lg border border-rule bg-surface p-4 md:p-6">
      <h1 className="text-h1 text-ink">{copy.title}</h1>
      <p className="mt-1 text-body text-ink-muted">{copy.intro}</p>

      <form onSubmit={submit} className="mt-6 flex flex-col gap-4" noValidate>
        {formLevelError ? (
          <Notice tone="danger" title="Account not created">
            {formLevelError}
          </Notice>
        ) : null}
        <Field label="Your name" required error={fieldError("full_name")}>
          {(control) => (
            <input
              {...control}
              autoComplete="name"
              value={form.fullName}
              maxLength={120}
              onChange={(e) => set("fullName")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field
          label="Business name"
          required
          hint={copy.businessHint}
          error={fieldError("business_name")}
        >
          {(control) => (
            <input
              {...control}
              autoComplete="organization"
              value={form.businessName}
              maxLength={200}
              onChange={(e) => set("businessName")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field label="Email" required error={fieldError("email")}>
          {(control) => (
            <input
              {...control}
              type="email"
              autoComplete="email"
              value={form.email}
              maxLength={254}
              onChange={(e) => set("email")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field
          label="Password"
          required
          hint={copy.passwordHint}
          error={
            fieldError("password") ??
            (shortPassword ? `Use at least ${MIN_PASSWORD} characters.` : undefined)
          }
        >
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="new-password"
              value={form.password}
              maxLength={128}
              onChange={(e) => set("password")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <label className="flex items-start gap-3 text-small text-ink">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-0.5 size-4 shrink-0 accent-primary"
          />
          <span>{copy.termsLabel}</span>
        </label>
        {fieldError("accept_terms_version") ? (
          <p className="text-small text-danger">{fieldError("accept_terms_version")}</p>
        ) : null}
        <Button type="submit" loading={busy} disabled={!ready}>
          {copy.submit}
        </Button>
      </form>

      <p className="mt-6 text-small text-ink-muted">
        {copy.switchPrompt}{" "}
        <Link
          href={`/login${next !== "/app" ? `?next=${encodeURIComponent(next)}` : ""}`}
          className="font-medium text-info hover:text-primary hover:underline"
        >
          {copy.switchLink}
        </Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
