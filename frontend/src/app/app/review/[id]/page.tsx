"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field, textareaClass } from "@/components/ui/Fields";
import { HashChip } from "@/components/ui/HashChip";
import { Icon } from "@/components/ui/Icon";
import { ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { PageHeader } from "@/components/ui/PageHeader";
import { onboardingCopy, onboardingStatusLabel } from "@/content/onboarding";
import {
  checkFieldLabel,
  checkResultLabel,
  checkResultTone,
  checkSourceLabel,
  decisionOptions,
  evidenceLevelCopy,
  reviewCopy as copy,
  submissionStatusLabel,
  submissionStatusTone,
} from "@/content/review";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type {
  OnboardingStatus,
  CheckField,
  CheckResult,
  CheckSource,
  ReviewCheck,
  ReviewCheckBody,
  ReviewDecision,
  ReviewDecisionBody,
  ReviewDetail,
} from "@/lib/api/types";
import { formatBytes, formatDate, formatTimestamp, todayInIndia } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

const FIELDS = Object.keys(checkFieldLabel) as CheckField[];
const SOURCES = Object.keys(checkSourceLabel) as CheckSource[];
const RESULTS = Object.keys(checkResultLabel) as CheckResult[];

function submissionPath(id: string): string {
  return `/review/submissions/${encodeURIComponent(id)}`;
}

export default function ReviewSubmissionPage() {
  const params = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApiGet<ReviewDetail>(submissionPath(params.id));
  const [latest, setLatest] = useState<ReviewDetail | null>(null);
  const current = latest && latest.submission_id === params.id ? latest : data;

  if (error)
    return <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />;
  if (loading || !current) return <LoadingBlock label="Loading the submission" />;

  const pending = current.decision === null;
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <Link
        href="/app/review"
        className="inline-flex items-center gap-1 self-start text-small font-medium text-info hover:text-primary hover:underline"
      >
        {copy.back}
      </Link>
      <PageHeader
        title={current.profile.enterprise_name ?? current.profile.udyam_number ?? "Submission"}
        description={`${copy.revision(current.revision)} · ${formatTimestamp(current.submitted_at)}`}
        actions={
          <span data-testid="review-status">
            <Badge tone={submissionStatusTone[current.status]}>
              {submissionStatusLabel[current.status]}
            </Badge>
          </span>
        }
      />
      <Notice title={copy.boundaryTitle}>{copy.boundary}</Notice>
      <EvidenceLevelCard detail={current} />
      {current.own_submission ? <Notice tone="warning">{copy.ownNotice}</Notice> : null}
      <SubmittedCard detail={current} />
      <CertificateCard detail={current} />
      <ClaimsCard detail={current} />
      <ChecksCard
        detail={current}
        onChange={setLatest}
        canRecord={pending && !current.own_submission}
      />
      <DecisionCard detail={current} onChange={setLatest} />
      <HistoryCard detail={current} />
    </div>
  );
}

function EvidenceLevelCard({ detail }: { detail: ReviewDetail }) {
  const level = evidenceLevelCopy[detail.evidence_level];
  return (
    <Card title={copy.evidenceTitle}>
      <div data-testid="evidence-level" className="flex flex-col gap-2">
        <div>
          <Badge tone={detail.evidence_level === "official_record_matched" ? "success" : "neutral"}>
            {level.label}
          </Badge>
        </div>
        <p className="text-small text-ink-muted">{level.body}</p>
      </div>
    </Card>
  );
}

function Rows({ rows }: { rows: [string, ReactNode][] }) {
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

function SubmittedCard({ detail }: { detail: ReviewDetail }) {
  const p = detail.profile;
  const labels = onboardingCopy.labels;
  const cls = onboardingCopy.classes.find((c) => c.value === p.enterprise_class)?.label;
  const role = onboardingCopy.roles.find((r) => r.value === p.representative_role)?.label;
  return (
    <Card title={copy.submittedTitle} description={copy.submittedNotice}>
      <div data-testid="submitted-details">
        <Rows
          rows={[
            [labels.enterprise_name, p.enterprise_name],
            [labels.udyam_number, p.udyam_number],
            [labels.enterprise_class, cls ? `${cls} (self-declared)` : null],
            [
              labels.registration_date,
              p.registration_date ? formatDate(p.registration_date) : null,
            ],
            [
              onboardingCopy.sections.address,
              [p.address_line1, p.address_line2, p.city, p.state, p.pin_code]
                .filter(Boolean)
                .join(", ") || null,
            ],
            [labels.contact_email, p.contact_email],
            [labels.contact_phone, p.contact_phone],
            [labels.representative_name, p.representative_name],
            [labels.representative_role, role],
            [labels.authorisation_note, p.authorisation_note],
            ["Authority confirmed", p.authority_confirmed ? "Yes" : "No"],
            [copy.submittedBy, `${detail.submitted_by.full_name} (${detail.submitted_by.email})`],
          ]}
        />
      </div>
      <div className="mt-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-small text-ink-muted">{copy.snapshot}:</span>
          <HashChip hash={detail.snapshot_sha256} label="Snapshot" />
        </div>
        <Notice tone={detail.snapshot_intact ? "success" : "danger"}>
          {detail.snapshot_intact ? copy.snapshotIntact : copy.snapshotBroken}
        </Notice>
      </div>
    </Card>
  );
}

function CertificateCard({ detail }: { detail: ReviewDetail }) {
  const c = detail.certificate;
  return (
    <Card title={copy.certificateTitle}>
      <div className="flex flex-col gap-3">
        <p className="break-all text-body text-ink">
          {c.original_filename}{" "}
          <span className="text-small text-ink-muted">
            · {formatBytes(c.size_bytes)} · uploaded {formatTimestamp(c.uploaded_at)}
          </span>
        </p>
        <HashChip hash={c.sha256} />
        <Notice tone={c.bytes_intact ? "info" : "danger"}>
          {c.bytes_intact ? copy.certificateIntact : copy.certificateBroken}
        </Notice>
        <div className="flex flex-col gap-1">
          <a
            href={`/api/v1${submissionPath(detail.submission_id)}/certificate`}
            data-testid="review-certificate-download"
            className="inline-flex h-10 items-center gap-2 self-start rounded-md border border-rule-strong px-4 text-small font-medium text-ink transition-colors duration-150 hover:border-ink hover:bg-surface-subtle"
          >
            <Icon name="download" className="size-4" />
            {copy.downloadCertificate}
          </a>
          <p className="text-caption text-ink-muted">{copy.downloadHint}</p>
        </div>
      </div>
    </Card>
  );
}

function ClaimsCard({ detail }: { detail: ReviewDetail }) {
  return (
    <Card title={copy.claimsTitle}>
      {detail.other_claims.length === 0 ? (
        <p className="text-small text-ink-muted">{copy.claimsNone}</p>
      ) : (
        <div className="flex flex-col gap-3" data-testid="other-claims">
          <Notice tone="warning">{copy.claimsIntro}</Notice>
          <ul className="divide-y divide-rule">
            {detail.other_claims.map((claim) => (
              <li
                key={claim.supplier_id}
                className="flex flex-col gap-1 py-2.5 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-body text-ink">
                    {claim.enterprise_name ?? "Unnamed enterprise"}
                  </span>
                  <Badge tone="neutral">
                    {onboardingStatusLabel[claim.profile_status as OnboardingStatus] ??
                      claim.profile_status}
                  </Badge>
                  {claim.contested ? <Badge tone="warning">Contested</Badge> : null}
                </div>
                {claim.submission_id ? (
                  <Link
                    href={`/app/review/${encodeURIComponent(claim.submission_id)}`}
                    className="text-small font-medium text-info hover:text-primary hover:underline"
                  >
                    {copy.openClaim}
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function CheckView({ check }: { check: ReviewCheck }) {
  return (
    <li className="flex flex-col gap-2 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-body font-medium text-ink">{checkSourceLabel[check.source]}</span>
        {check.official_source ? <Badge tone="primary">Official record</Badge> : null}
      </div>
      <p className="break-words text-small text-ink">{check.source_detail}</p>
      <p className="text-small text-ink-muted">
        Checked {formatDate(check.checked_on)} {copy.by(check.reviewer.full_name)} · recorded{" "}
        {formatTimestamp(check.recorded_at)}
      </p>
      <ul className="flex flex-col gap-1.5">
        {check.items.map((item) => (
          <li key={item.field} className="flex flex-col gap-0.5 rounded-md bg-surface-subtle p-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-small font-medium text-ink">{checkFieldLabel[item.field]}</span>
              <Badge tone={checkResultTone[item.result]}>{checkResultLabel[item.result]}</Badge>
            </div>
            <p className="break-words text-caption text-ink-muted">
              Submitted: {item.submitted_value ?? "—"} · Seen: {item.observed_value ?? "—"}
            </p>
          </li>
        ))}
      </ul>
      {check.note ? <p className="text-small text-ink-muted">Note: {check.note}</p> : null}
    </li>
  );
}

type Row = { result: CheckResult | ""; observed: string };

function ChecksCard({
  detail,
  onChange,
  canRecord,
}: {
  detail: ReviewDetail;
  onChange: (d: ReviewDetail) => void;
  canRecord: boolean;
}) {
  return (
    <Card title={copy.checksTitle} description={copy.checksIntro}>
      {detail.checks.length === 0 ? (
        <p className="text-small text-ink-muted">{copy.checksNone}</p>
      ) : (
        <ul className="divide-y divide-rule" data-testid="review-checks">
          {detail.checks.map((check) => (
            <CheckView key={check.id} check={check} />
          ))}
        </ul>
      )}
      {canRecord ? <CheckForm detail={detail} onChange={onChange} /> : null}
    </Card>
  );
}

function CheckForm({
  detail,
  onChange,
}: {
  detail: ReviewDetail;
  onChange: (d: ReviewDetail) => void;
}) {
  const [source, setSource] = useState<CheckSource>("udyam_portal");
  const [sourceDetail, setSourceDetail] = useState("");
  const [checkedOn, setCheckedOn] = useState(todayInIndia());
  const [note, setNote] = useState("");
  const [rows, setRows] = useState<Record<CheckField, Row>>(
    () =>
      Object.fromEntries(FIELDS.map((f) => [f, { result: "", observed: "" }])) as Record<
        CheckField,
        Row
      >,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);

  function setRow(field: CheckField, change: Partial<Row>) {
    setRows((r) => ({ ...r, [field]: { ...r[field], ...change } }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setDone(false);
    const body: ReviewCheckBody = {
      source,
      source_detail: sourceDetail,
      checked_on: checkedOn,
      note: note.trim() === "" ? null : note,
      items: FIELDS.filter((f) => rows[f].result !== "").map((f) => ({
        field: f,
        result: rows[f].result as CheckResult,
        observed_value: rows[f].observed.trim() === "" ? null : rows[f].observed,
      })),
    };
    try {
      const updated = await api<ReviewDetail>(`${submissionPath(detail.submission_id)}/checks`, {
        method: "POST",
        json: body,
      });
      onChange(updated);
      setDone(true);
      setSourceDetail("");
      setNote("");
      setRows(
        Object.fromEntries(FIELDS.map((f) => [f, { result: "", observed: "" }])) as Record<
          CheckField,
          Row
        >,
      );
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(false);
    }
  }

  const submitted = (field: CheckField): string | null => {
    const p = detail.profile;
    if (field === "address")
      return (
        [p.address_line1, p.address_line2, p.city, p.state, p.pin_code]
          .filter(Boolean)
          .join(", ") || null
      );
    const value = p[field];
    return value === null || value === undefined ? null : String(value);
  };

  return (
    <form
      onSubmit={submit}
      className="mt-6 flex flex-col gap-4 border-t border-rule pt-5"
      data-testid="check-form"
    >
      <h3 className="text-h3 text-ink">{copy.checkForm}</h3>
      <Field label={copy.sourceLabel} required error={error?.forField("source")}>
        {(control) => (
          <select
            {...control}
            className={controlClass}
            value={source}
            onChange={(e) => setSource(e.target.value as CheckSource)}
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {checkSourceLabel[s]}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field
        label={copy.sourceDetailLabel}
        hint={copy.sourceDetailHint}
        required
        error={error?.forField("source_detail")}
      >
        {(control) => (
          <input
            {...control}
            className={controlClass}
            value={sourceDetail}
            maxLength={300}
            onChange={(e) => setSourceDetail(e.target.value)}
          />
        )}
      </Field>
      <Field
        label={copy.checkedOnLabel}
        hint={copy.checkedOnHint}
        required
        error={error?.forField("checked_on")}
      >
        {(control) => (
          <input
            {...control}
            type="date"
            className={controlClass}
            value={checkedOn}
            max={todayInIndia()}
            onChange={(e) => setCheckedOn(e.target.value)}
          />
        )}
      </Field>
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-2 text-small font-medium text-ink">{copy.itemsLegend}</legend>
        {FIELDS.map((field) => (
          <div key={field} className="flex flex-col gap-2 rounded-md border border-rule p-3">
            <p className="text-small font-medium text-ink">{checkFieldLabel[field]}</p>
            <p className="break-words text-caption text-ink-muted">
              Submitted: {submitted(field) ?? "Not provided"}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label={`${copy.resultLabel}: ${checkFieldLabel[field]}`}>
                {(control) => (
                  <select
                    {...control}
                    className={controlClass}
                    value={rows[field].result}
                    onChange={(e) => setRow(field, { result: e.target.value as CheckResult | "" })}
                  >
                    <option value="">{copy.notCompared}</option>
                    {RESULTS.map((r) => (
                      <option key={r} value={r}>
                        {checkResultLabel[r]}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
              <Field label={`${copy.observedLabel}: ${checkFieldLabel[field]}`}>
                {(control) => (
                  <input
                    {...control}
                    className={controlClass}
                    value={rows[field].observed}
                    maxLength={500}
                    disabled={rows[field].result === ""}
                    onChange={(e) => setRow(field, { observed: e.target.value })}
                  />
                )}
              </Field>
            </div>
          </div>
        ))}
      </fieldset>
      <Field label={copy.noteLabel} error={error?.forField("note")}>
        {(control) => (
          <textarea
            {...control}
            className={textareaClass}
            value={note}
            maxLength={2000}
            onChange={(e) => setNote(e.target.value)}
          />
        )}
      </Field>
      {error ? <Notice tone="danger">{error.message}</Notice> : null}
      {done ? <Notice tone="success">{copy.checkRecorded}</Notice> : null}
      <div>
        <Button type="submit" variant="secondary" loading={busy}>
          {copy.recordCheck}
        </Button>
      </div>
    </form>
  );
}

function DecisionView({ decision, testId }: { decision: ReviewDecision; testId?: string }) {
  return (
    <div className="flex flex-col gap-1" data-testid={testId}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={submissionStatusTone[decision.decision]}>
          {submissionStatusLabel[decision.decision]}
        </Badge>
        <span className="text-small text-ink-muted">
          {formatTimestamp(decision.decided_at)} {copy.by(decision.reviewer.full_name)}
        </span>
      </div>
      <p className="break-words text-small text-ink">
        <span className="text-ink-muted">{copy.reasonLabel}:</span> {decision.reason}
      </p>
      {decision.internal_note ? (
        <p className="break-words text-small text-ink">
          <span className="text-ink-muted">{copy.internalNote}:</span> {decision.internal_note}
        </p>
      ) : null}
    </div>
  );
}

function DecisionCard({
  detail,
  onChange,
}: {
  detail: ReviewDetail;
  onChange: (d: ReviewDetail) => void;
}) {
  return (
    <Card title={copy.decisionTitle} description={copy.decisionIntro}>
      {detail.decision ? (
        <DecisionView decision={detail.decision} testId="review-decision" />
      ) : detail.own_submission ? (
        <p className="text-small text-ink-muted">{copy.ownNotice}</p>
      ) : (
        <DecisionForm detail={detail} onChange={onChange} />
      )}
    </Card>
  );
}

function DecisionForm({
  detail,
  onChange,
}: {
  detail: ReviewDetail;
  onChange: (d: ReviewDetail) => void;
}) {
  const [decision, setDecision] = useState<ReviewDecisionBody["decision"] | "">("");
  const [reason, setReason] = useState("");
  const [internalNote, setInternalNote] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const label = decisionOptions.find((o) => o.value === decision)?.label ?? "";

  async function record() {
    if (!decision) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api<ReviewDetail>(`${submissionPath(detail.submission_id)}/decision`, {
        method: "POST",
        json: {
          decision,
          reason,
          internal_note: internalNote.trim() === "" ? null : internalNote,
        } satisfies ReviewDecisionBody,
      });
      onChange(updated);
    } catch (e) {
      setError(asApiError(e));
      setConfirming(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      data-testid="decision-form"
      onSubmit={(event) => {
        event.preventDefault();
        setConfirming(true);
      }}
    >
      {detail.approval_blockers.length > 0 ? (
        <Notice tone="warning" title="Approval is not available yet">
          <ul className="list-disc pl-5">
            {detail.approval_blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </Notice>
      ) : null}
      <fieldset>
        <legend className="mb-2 text-small font-medium text-ink">{copy.decisionLabel}</legend>
        <div className="flex flex-col gap-2">
          {decisionOptions.map((option) => {
            const allowed = detail.allowed_decisions.includes(option.value);
            return (
              <label
                key={option.value}
                className={`flex min-h-11 items-center gap-3 rounded-md border border-rule px-3 ${
                  allowed ? "cursor-pointer text-ink" : "cursor-not-allowed text-ink-faint"
                }`}
              >
                <input
                  type="radio"
                  name="decision"
                  value={option.value}
                  disabled={!allowed}
                  checked={decision === option.value}
                  onChange={() => {
                    setDecision(option.value);
                    setConfirming(false);
                  }}
                  className="size-4 shrink-0 accent-primary"
                />
                <span className="text-body">{option.label}</span>
              </label>
            );
          })}
        </div>
      </fieldset>
      <Field
        label={copy.reasonLabel}
        hint={copy.reasonHint}
        required
        error={error?.forField("reason")}
      >
        {(control) => (
          <textarea
            {...control}
            className={textareaClass}
            value={reason}
            maxLength={2000}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
      </Field>
      <Field
        label={copy.internalNoteLabel}
        hint={copy.internalNoteHint}
        error={error?.forField("internal_note")}
      >
        {(control) => (
          <textarea
            {...control}
            className={textareaClass}
            value={internalNote}
            maxLength={2000}
            onChange={(e) => setInternalNote(e.target.value)}
          />
        )}
      </Field>
      {error ? <Notice tone="danger">{error.message}</Notice> : null}
      {confirming ? (
        <Notice tone="warning" title={copy.confirmDecision(label)}>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button loading={busy} onClick={() => void record()}>
              Confirm
            </Button>
            <Button variant="secondary" disabled={busy} onClick={() => setConfirming(false)}>
              Cancel
            </Button>
          </div>
        </Notice>
      ) : (
        <div>
          <Button type="submit" disabled={!decision || reason.trim().length < 10}>
            {copy.submitDecision}
          </Button>
        </div>
      )}
    </form>
  );
}

function HistoryCard({ detail }: { detail: ReviewDetail }) {
  return (
    <Card title={copy.historyTitle}>
      <ul className="divide-y divide-rule" data-testid="review-history">
        {detail.history.map((item) => (
          <li key={item.submission_id} className="flex flex-col gap-2 py-3">
            <div className="flex flex-wrap items-center gap-2">
              {item.submission_id === detail.submission_id ? (
                <span className="text-body font-medium text-ink">
                  {copy.revision(item.revision)}
                </span>
              ) : (
                <Link
                  href={`/app/review/${encodeURIComponent(item.submission_id)}`}
                  className="text-body font-medium text-info hover:text-primary hover:underline"
                >
                  {copy.revision(item.revision)}
                </Link>
              )}
              <span className="text-small text-ink-muted">
                {formatTimestamp(item.submitted_at)}
              </span>
              <Badge tone={submissionStatusTone[item.status]}>
                {submissionStatusLabel[item.status]}
              </Badge>
            </div>
            {item.decision ? <DecisionView decision={item.decision} /> : null}
            <HashChip hash={item.snapshot_sha256} label="Snapshot" />
          </li>
        ))}
      </ul>
    </Card>
  );
}
