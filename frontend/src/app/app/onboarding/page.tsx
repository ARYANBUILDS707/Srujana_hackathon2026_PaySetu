"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field, textareaClass } from "@/components/ui/Fields";
import { HashChip } from "@/components/ui/HashChip";
import { ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { Progress } from "@/components/ui/Progress";
import {
  onboardingCopy as copy,
  onboardingStatusLabel,
  onboardingStatusTone,
} from "@/content/onboarding";
import { api, apiUpload, asApiError, type ApiError } from "@/lib/api/client";
import type { Onboarding, OnboardingDraft } from "@/lib/api/types";
import { formatBytes, formatDate, formatTimestamp } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

type FormState = Record<string, string> & { authority_confirmed: string };

const TEXT_FIELDS = [
  "enterprise_name",
  "udyam_number",
  "enterprise_class",
  "registration_date",
  "address_line1",
  "address_line2",
  "city",
  "state",
  "pin_code",
  "contact_email",
  "contact_phone",
  "representative_name",
  "representative_role",
  "authorisation_note",
] as const;

function toForm(data: Onboarding): FormState {
  const form = { authority_confirmed: data.authority_confirmed ? "yes" : "" } as FormState;
  for (const field of TEXT_FIELDS) form[field] = (data[field] as string | null) ?? "";
  return form;
}

function toDraft(form: FormState): OnboardingDraft {
  const draft: Record<string, unknown> = {
    authority_confirmed: form.authority_confirmed === "yes",
  };
  for (const field of TEXT_FIELDS) draft[field] = form[field].trim() === "" ? null : form[field];
  return draft as OnboardingDraft;
}

/** Client-side preview only; the server normalises and validates authoritatively. */
function udyamPreview(value: string): string | null {
  const core = value.replace(/[\s\-_/.]/g, "").toUpperCase();
  const match = /^UDYAM([A-Z]{2})(\d{2})(\d{7})$/.exec(core);
  return match ? `UDYAM-${match[1]}-${match[2]}-${match[3]}` : null;
}

function certificateHref(id: string): string {
  return `/api/v1/onboarding/certificates/${encodeURIComponent(id)}/download`;
}

export default function OnboardingPage() {
  const { data, error, loading, reload } = useApiGet<Onboarding>("/onboarding");
  const [latest, setLatest] = useState<Onboarding | null>(null);
  const current = latest ?? data;

  if (error)
    return <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />;
  if (loading || !current) return <LoadingBlock label="Loading business profile" />;

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <PageHeader
        title={copy.title}
        description={copy.description}
        actions={
          <Badge tone={onboardingStatusTone[current.status]}>
            {onboardingStatusLabel[current.status]}
          </Badge>
        }
      />
      {current.editable ? (
        <Editor key={current.submissions.length} data={current} onChange={setLatest} />
      ) : (
        <Submitted data={current} />
      )}
    </div>
  );
}

function Editor({ data, onChange }: { data: Onboarding; onChange: (d: Onboarding) => void }) {
  const [form, setForm] = useState<FormState>(() => toForm(data));
  const [step, setStep] = useState<"edit" | "review">("edit");
  const [busy, setBusy] = useState<"save" | "submit" | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState(false);
  const set = (key: string) => (value: string) => {
    setSaved(false);
    setError(null); // a server error describes the old value, not the one being typed
    setForm((f) => ({ ...f, [key]: value }));
  };
  const fieldError = (name: string) => error?.forField(name);

  async function save(): Promise<Onboarding | null> {
    setBusy("save");
    setError(null);
    try {
      const result = await api<Onboarding>("/onboarding/draft", {
        method: "PUT",
        json: toDraft(form),
      });
      onChange(result);
      setSaved(true);
      return result;
    } catch (e) {
      setError(asApiError(e));
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    await save();
  }

  async function toReview() {
    const result = await save();
    if (result) {
      setStep("review");
      window.scrollTo({ top: 0 });
    }
  }

  async function submit() {
    setBusy("submit");
    setError(null);
    try {
      onChange(await api<Onboarding>("/onboarding/submit", { method: "POST" }));
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(null);
    }
  }

  const formLevelError = error && error.fieldErrors.length === 0 ? error.message : null;

  if (step === "review") {
    return (
      <Card title={copy.reviewTitle} description={copy.reviewIntro}>
        <div className="flex flex-col gap-5" data-testid="onboarding-review">
          {data.missing_for_submission.length > 0 ? (
            <Notice tone="warning" title={copy.missingTitle}>
              <ul className="list-disc pl-5">
                {data.missing_for_submission.map((field) => (
                  <li key={field}>{copy.labels[field] ?? field}</li>
                ))}
              </ul>
            </Notice>
          ) : null}
          {data.udyam_claim_conflict ? <Notice tone="warning">{copy.claimConflict}</Notice> : null}
          {error ? (
            <Notice tone="danger" title="Not submitted">
              {formLevelError ?? error.fieldErrors.map((e) => <p key={e.field}>{e.message}</p>)}
            </Notice>
          ) : null}
          <Summary data={data} />
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={submit}
              loading={busy === "submit"}
              disabled={data.missing_for_submission.length > 0}
            >
              {copy.submit}
            </Button>
            <Button variant="secondary" onClick={() => setStep("edit")} disabled={busy !== null}>
              {copy.back}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  const preview = form.udyam_number ? udyamPreview(form.udyam_number) : null;

  return (
    <form onSubmit={onSave} className="flex flex-col gap-6" noValidate>
      {formLevelError ? (
        <Notice tone="danger" title="Not saved">
          {formLevelError}
        </Notice>
      ) : null}

      <Card title={copy.sections.enterprise}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <TextField name="enterprise_name" form={form} set={set} error={fieldError} max={200} />
          </div>
          <Field
            label={copy.labels.udyam_number}
            hint={
              form.udyam_number && !preview
                ? copy.udyamFormat
                : preview && preview !== form.udyam_number
                  ? copy.udyamPreview(preview)
                  : copy.hints.udyam_number
            }
            error={fieldError("udyam_number")}
          >
            {(control) => (
              <input
                {...control}
                value={form.udyam_number}
                maxLength={30}
                autoCapitalize="characters"
                spellCheck={false}
                placeholder="UDYAM-XX-00-0000000"
                onChange={(e) => set("udyam_number")(e.target.value)}
                className={`${controlClass} font-mono`}
              />
            )}
          </Field>
          <Field
            label={copy.labels.enterprise_class}
            hint={copy.hints.enterprise_class}
            error={fieldError("enterprise_class")}
          >
            {(control) => (
              <select
                {...control}
                value={form.enterprise_class}
                onChange={(e) => set("enterprise_class")(e.target.value)}
                className={controlClass}
              >
                <option value="">Choose…</option>
                {copy.classes.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <Field
            label={copy.labels.registration_date}
            hint={copy.hints.registration_date}
            error={fieldError("registration_date")}
          >
            {(control) => (
              <input
                {...control}
                type="date"
                value={form.registration_date}
                onChange={(e) => set("registration_date")(e.target.value)}
                className={controlClass}
              />
            )}
          </Field>
        </div>
        {data.udyam_claim_conflict ? (
          <div className="mt-4">
            <Notice tone="warning">{copy.claimConflict}</Notice>
          </div>
        ) : null}
      </Card>

      <Card title={copy.sections.address}>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <TextField name="address_line1" form={form} set={set} error={fieldError} max={200} />
          </div>
          <div className="md:col-span-2">
            <TextField name="address_line2" form={form} set={set} error={fieldError} max={200} />
          </div>
          <TextField name="city" form={form} set={set} error={fieldError} max={100} />
          <TextField name="state" form={form} set={set} error={fieldError} max={100} />
          <TextField
            name="pin_code"
            form={form}
            set={set}
            error={fieldError}
            max={7}
            inputMode="numeric"
          />
        </div>
      </Card>

      <Card title={copy.sections.contact}>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            name="contact_email"
            form={form}
            set={set}
            error={fieldError}
            max={254}
            type="email"
          />
          <TextField
            name="contact_phone"
            form={form}
            set={set}
            error={fieldError}
            max={16}
            type="tel"
          />
        </div>
      </Card>

      <Card title={copy.sections.representative}>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            name="representative_name"
            form={form}
            set={set}
            error={fieldError}
            max={120}
          />
          <Field label={copy.labels.representative_role} error={fieldError("representative_role")}>
            {(control) => (
              <select
                {...control}
                value={form.representative_role}
                onChange={(e) => set("representative_role")(e.target.value)}
                className={controlClass}
              >
                <option value="">Choose…</option>
                {copy.roles.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <div className="md:col-span-2">
            <Field
              label={copy.labels.authorisation_note}
              hint={copy.hints.authorisation_note}
              error={fieldError("authorisation_note")}
            >
              {(control) => (
                <textarea
                  {...control}
                  value={form.authorisation_note}
                  maxLength={500}
                  onChange={(e) => set("authorisation_note")(e.target.value)}
                  className={textareaClass}
                />
              )}
            </Field>
          </div>
          <label className="flex items-start gap-3 text-small text-ink md:col-span-2">
            <input
              type="checkbox"
              checked={form.authority_confirmed === "yes"}
              onChange={(e) => set("authority_confirmed")(e.target.checked ? "yes" : "")}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span>{copy.labels.authority_confirmed}</span>
          </label>
        </div>
      </Card>

      <CertificateCard data={data} onChange={onChange} />

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="submit"
          variant="secondary"
          loading={busy === "save"}
          disabled={busy !== null}
        >
          {copy.save}
        </Button>
        <Button onClick={toReview} disabled={busy !== null}>
          {copy.review}
        </Button>
        <span aria-live="polite" className="text-small text-success">
          {saved ? copy.saved : ""}
        </span>
      </div>
    </form>
  );
}

function TextField({
  name,
  form,
  set,
  error,
  max,
  type = "text",
  inputMode,
}: {
  name: string;
  form: FormState;
  set: (key: string) => (value: string) => void;
  error: (name: string) => string | undefined;
  max: number;
  type?: string;
  inputMode?: "numeric";
}) {
  return (
    <Field label={copy.labels[name]} hint={copy.hints[name]} error={error(name)}>
      {(control) => (
        <input
          {...control}
          type={type}
          inputMode={inputMode}
          value={form[name]}
          maxLength={max}
          onChange={(e) => set(name)(e.target.value)}
          className={controlClass}
        />
      )}
    </Field>
  );
}

function CertificateCard({
  data,
  onChange,
}: {
  data: Onboarding;
  onChange: (d: Onboarding) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);
  const [inputKey, setInputKey] = useState(0);

  async function upload() {
    if (!file) return;
    setError(null);
    setDone(false);
    setProgress(0);
    const form = new FormData();
    form.set("file", file);
    try {
      onChange(await apiUpload<Onboarding>("/onboarding/certificate", form, setProgress));
      setDone(true);
      setFile(null);
      setInputKey((k) => k + 1);
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setProgress(null);
    }
  }

  const certificate = data.certificate;
  return (
    <Card title={copy.sections.certificate}>
      <div className="flex flex-col gap-4">
        {certificate ? (
          <div
            className="flex flex-col gap-2 rounded-md border border-rule bg-surface-subtle p-3"
            data-testid="current-certificate"
          >
            <p className="text-small text-ink-muted">{copy.current}</p>
            <p className="break-all text-body font-medium text-ink">
              {certificate.original_filename}
            </p>
            <p className="text-small text-ink-muted">
              {formatBytes(certificate.size_bytes)} · uploaded{" "}
              {formatTimestamp(certificate.uploaded_at)}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <HashChip hash={certificate.sha256} />
              <a
                href={certificateHref(certificate.id)}
                className="text-small font-medium text-info hover:text-primary hover:underline"
              >
                {copy.download}
              </a>
            </div>
          </div>
        ) : null}
        <Field label={copy.labels.certificate} hint={copy.hints.certificate}>
          {(control) => (
            <input
              {...control}
              key={inputKey}
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => {
                setDone(false);
                setFile(e.target.files?.[0] ?? null);
              }}
              className="w-full text-small text-ink-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-control file:bg-surface file:px-3 file:py-1.5 file:font-medium file:text-ink"
            />
          )}
        </Field>
        {progress !== null ? (
          <div className="flex flex-col gap-1" aria-live="polite">
            <Progress value={Math.round(progress * 100)} max={100} label="Upload progress" />
            <p className="text-small text-ink-muted">
              {copy.uploading(Math.round(progress * 100))}
            </p>
          </div>
        ) : null}
        {error ? (
          <Notice tone="danger" title="Certificate not uploaded">
            {error.message}
          </Notice>
        ) : null}
        {done ? <Notice tone="success">{copy.uploaded}</Notice> : null}
        <div>
          <Button variant="secondary" onClick={upload} disabled={!file || progress !== null}>
            {certificate ? copy.replace : copy.upload}
          </Button>
        </div>
      </div>
    </Card>
  );
}

function Summary({ data }: { data: Onboarding }) {
  const role = copy.roles.find((r) => r.value === data.representative_role)?.label;
  const cls = copy.classes.find((c) => c.value === data.enterprise_class)?.label;
  const rows: [string, ReactNode][] = [
    [copy.labels.enterprise_name, data.enterprise_name],
    [copy.labels.udyam_number, data.udyam_number],
    [copy.labels.enterprise_class, cls ? `${cls} (self-declared)` : null],
    [
      copy.labels.registration_date,
      data.registration_date ? formatDate(data.registration_date) : null,
    ],
    [
      copy.sections.address,
      [data.address_line1, data.address_line2, data.city, data.state, data.pin_code]
        .filter(Boolean)
        .join(", ") || null,
    ],
    [copy.labels.contact_email, data.contact_email],
    [copy.labels.contact_phone, data.contact_phone],
    [copy.labels.representative_name, data.representative_name],
    [copy.labels.representative_role, role],
    [copy.labels.authorisation_note, data.authorisation_note],
    ["Authority confirmed", data.authority_confirmed ? "Yes" : "No"],
    [
      copy.labels.certificate,
      data.certificate ? (
        <a
          href={certificateHref(data.certificate.id)}
          className="break-all text-info hover:text-primary hover:underline"
        >
          {data.certificate.original_filename}
        </a>
      ) : null,
    ],
  ];
  return (
    <dl className="divide-y divide-rule">
      {rows.map(([label, value]) => (
        <div key={label} className="grid gap-1 py-2.5 sm:grid-cols-3 sm:gap-4">
          <dt className="text-small text-ink-muted">{label}</dt>
          <dd className="break-words text-body text-ink sm:col-span-2">
            {value ?? <span className="text-ink-muted">Not provided</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function Submitted({ data }: { data: Onboarding }) {
  return (
    <>
      <Card>
        <div data-testid="onboarding-submitted" className="flex flex-col gap-4">
          <h2 className="text-h2 text-ink">{copy.submittedTitle}</h2>
          <Notice tone="success">{copy.submittedBody}</Notice>
          <p className="text-small text-ink-muted">{copy.reviewNotAvailable}</p>
          {data.submitted_at ? (
            <p className="text-small text-ink-muted">
              Submitted {formatTimestamp(data.submitted_at)}
            </p>
          ) : null}
        </div>
      </Card>
      <Card title={copy.reviewTitle}>
        <Summary data={data} />
      </Card>
      {data.submissions.length > 0 ? (
        <Card title={copy.history}>
          <ul className="divide-y divide-rule">
            {data.submissions.map((s) => (
              <li key={s.revision} className="flex flex-col gap-2 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-body font-medium text-ink">
                    {copy.revision(s.revision)}
                  </span>
                  <span className="text-small text-ink-muted">
                    {formatTimestamp(s.submitted_at)}
                  </span>
                  {s.claim_contested ? <Badge tone="warning">{copy.contested}</Badge> : null}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-small text-ink-muted">{copy.fingerprint}:</span>
                  <HashChip hash={s.snapshot_sha256} label="Snapshot" />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </>
  );
}
