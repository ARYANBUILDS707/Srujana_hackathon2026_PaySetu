"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field } from "@/components/ui/Fields";
import { Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { authCopy } from "@/content/auth";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { PasswordUpdated } from "@/lib/api/types";
import { useSession } from "@/lib/session/SessionContext";

const copy = authCopy.settings;
const MIN_PASSWORD = 10;

function ChangePassword({ email }: { email: string }) {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState<PasswordUpdated["notification"] | null>(null);
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const mismatch = form.confirm.length > 0 && form.confirm !== form.next;
  const shortPassword = form.next.length > 0 && form.next.length < MIN_PASSWORD;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const result = await api<PasswordUpdated>("/auth/change-password", {
        method: "POST",
        json: { current_password: form.current, new_password: form.next },
      });
      setForm({ current: "", next: "", confirm: "" });
      setDone(result.notification);
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={copy.changeTitle} description={copy.changeDescription}>
      <form onSubmit={submit} className="flex max-w-md flex-col gap-4" noValidate>
        {done ? (
          <div data-testid="password-changed">
            <Notice tone="success" title={copy.doneTitle}>
              {copy.doneBody} {done === "sent" ? `${copy.noticeSent} ${email}.` : copy.noticeFailed}
            </Notice>
          </div>
        ) : null}
        {error && error.fieldErrors.length === 0 ? (
          <Notice tone="danger" title="Password not changed">
            {error.message}
          </Notice>
        ) : null}
        <Field label={copy.current} required error={error?.forField("current_password")}>
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="current-password"
              value={form.current}
              maxLength={128}
              onChange={(e) => set("current")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field
          label={copy.next}
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
              value={form.next}
              maxLength={128}
              onChange={(e) => set("next")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <Field label={copy.confirm} required error={mismatch ? authCopy.reset.mismatch : undefined}>
          {(control) => (
            <input
              {...control}
              type="password"
              autoComplete="new-password"
              value={form.confirm}
              maxLength={128}
              onChange={(e) => set("confirm")(e.target.value)}
              className={controlClass}
            />
          )}
        </Field>
        <div>
          <Button
            type="submit"
            loading={busy}
            disabled={
              !form.current || form.next.length < MIN_PASSWORD || form.confirm !== form.next
            }
          >
            {copy.submit}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function SignOutEverywhere() {
  const { signOutEverywhere } = useSession();
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await signOutEverywhere();
    } catch (e) {
      setError(asApiError(e));
      setBusy(false);
    }
  }

  return (
    <Card title={copy.everywhereTitle} description={copy.everywhereDescription}>
      {error ? (
        <div className="mb-4">
          <Notice tone="danger" title="Sessions not ended">
            {error.message}
          </Notice>
        </div>
      ) : null}
      {confirming ? (
        <div className="flex flex-wrap gap-3">
          <Button variant="danger" loading={busy} onClick={run}>
            {copy.everywhereConfirm}
          </Button>
          <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
            {copy.cancel}
          </Button>
        </div>
      ) : (
        <Button variant="secondary" onClick={() => setConfirming(true)}>
          {copy.everywhereButton}
        </Button>
      )}
    </Card>
  );
}

export default function SettingsPage() {
  const { me } = useSession();
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <PageHeader title={copy.title} description={copy.description} />
      <Card title={copy.accountTitle}>
        <dl className="grid gap-x-8 gap-y-2 text-body sm:grid-cols-[auto_1fr]">
          <dt className="text-small text-ink-muted">Name</dt>
          <dd className="break-words text-ink">{me.user.full_name}</dd>
          <dt className="text-small text-ink-muted">Email</dt>
          <dd className="break-all text-ink">{me.user.email}</dd>
          <dt className="text-small text-ink-muted">Business</dt>
          <dd className="break-words text-ink">{me.supplier.legal_name}</dd>
        </dl>
      </Card>
      <ChangePassword email={me.user.email} />
      <SignOutEverywhere />
    </div>
  );
}
