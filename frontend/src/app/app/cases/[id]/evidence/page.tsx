"use client";

import { useParams } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { useCase } from "@/components/cases/CaseContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field } from "@/components/ui/Fields";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { HashChip } from "@/components/ui/HashChip";
import { evidenceKindLabel, uploadKinds } from "@/content/app";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { Evidence, EvidenceKind, Integrity } from "@/lib/api/types";
import { formatBytes, formatTimestamp } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const { reload: reloadCase } = useCase();
  const evidence = useApiGet<Evidence[]>(`/cases/${params.id}/evidence`);

  const fileInput = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState<EvidenceKind>("invoice");
  const [note, setNote] = useState("");
  const [fileName, setFileName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [justAdded, setJustAdded] = useState<Evidence | null>(null);

  const [checking, setChecking] = useState(false);
  const [integrity, setIntegrity] = useState<Integrity | null>(null);
  const [integrityError, setIntegrityError] = useState<ApiError | null>(null);

  async function upload(event: FormEvent) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setUploadError(asApiError(null));
      return;
    }
    setUploading(true);
    setUploadError(null);
    setJustAdded(null);
    const form = new FormData();
    form.set("file", file);
    form.set("kind", kind);
    if (note.trim()) form.set("note", note.trim());
    try {
      const added = await api<Evidence>(`/cases/${params.id}/evidence`, { method: "POST", form });
      setJustAdded(added);
      setNote("");
      setFileName("");
      if (fileInput.current) fileInput.current.value = "";
      evidence.reload();
      reloadCase();
    } catch (e) {
      setUploadError(asApiError(e));
    } finally {
      setUploading(false);
    }
  }

  async function verify() {
    setChecking(true);
    setIntegrityError(null);
    try {
      setIntegrity(await api<Integrity>(`/cases/${params.id}/integrity-check`, { method: "POST" }));
      reloadCase();
    } catch (e) {
      setIntegrityError(asApiError(e));
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card
        title="Add evidence"
        description="Files are stored unchanged and fingerprinted with SHA-256 on the server."
      >
        <form onSubmit={upload} className="flex flex-col gap-4" noValidate>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Type of evidence" required>
              {(control) => (
                <select
                  {...control}
                  value={kind}
                  onChange={(e) => setKind(e.target.value as EvidenceKind)}
                  className={controlClass}
                >
                  {uploadKinds.map((k) => (
                    <option key={k} value={k}>
                      {evidenceKindLabel[k]}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <Field
              label="File"
              required
              hint="PDF, JPEG, PNG, HEIC, email (.eml) or UTF-8 text. Up to 15 MB."
            >
              {(control) => (
                <input
                  {...control}
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.heic,.eml,.txt,application/pdf,image/*,message/rfc822,text/plain"
                  onChange={(e) => setFileName(e.target.files?.[0]?.name ?? "")}
                  className={`${controlClass} py-2 file:mr-3 file:rounded-md file:border-0 file:bg-primary-tint file:px-3 file:py-1 file:font-medium file:text-primary`}
                />
              )}
            </Field>
          </div>
          <Field label="Note" hint="Optional. What this file shows.">
            {(control) => (
              <input
                {...control}
                value={note}
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
                className={controlClass}
              />
            )}
          </Field>
          {uploadError ? (
            <Notice tone="danger" title="This file was not added">
              {uploadError.code === "unknown" ? "Choose a file first." : uploadError.message}
            </Notice>
          ) : null}
          {justAdded ? (
            <Notice tone="success" title="Evidence added and sealed">
              {justAdded.original_filename} was stored and fingerprinted. Its SHA-256 is shown in
              the list below.
            </Notice>
          ) : null}
          <div>
            <Button type="submit" loading={uploading} disabled={!fileName && !uploading}>
              Add evidence
            </Button>
          </div>
        </form>
      </Card>

      <Card
        title="Evidence Vault"
        description="Everything stored for this case, with its recorded hash."
        actions={
          <Button variant="secondary" onClick={verify} loading={checking}>
            Verify integrity
          </Button>
        }
      >
        {integrityError ? (
          <div className="mb-4">
            <ErrorState message={integrityError.message} requestId={integrityError.requestId} />
          </div>
        ) : null}
        {integrity ? <IntegrityResult result={integrity} /> : null}

        {evidence.error ? (
          <ErrorState
            message={evidence.error.message}
            requestId={evidence.error.requestId}
            onRetry={evidence.reload}
          />
        ) : evidence.loading ? (
          <LoadingBlock label="Loading evidence" />
        ) : (evidence.data ?? []).length === 0 ? (
          <EmptyState
            title="No evidence yet"
            body="Start with the invoice and proof of delivery, such as the signed challan."
          />
        ) : (
          <ul className="divide-y divide-rule" data-testid="evidence-list">
            {evidence.data?.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-2 py-4 md:flex-row md:items-start md:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-body font-medium text-ink">
                    {item.original_filename}
                  </p>
                  <p className="text-small text-ink-muted">
                    {evidenceKindLabel[item.kind]} · {item.mime_type} ·{" "}
                    {formatBytes(item.size_bytes)} · recorded {formatTimestamp(item.received_at)}
                  </p>
                  {item.note ? <p className="mt-1 text-small text-ink">{item.note}</p> : null}
                </div>
                <div className="flex flex-col items-start gap-2 md:items-end">
                  <HashChip hash={item.sha256} />
                  <a
                    href={`/api/v1/evidence/${item.id}/download`}
                    className="text-small font-medium text-primary hover:text-primary-hover"
                  >
                    Download original
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function IntegrityResult({ result }: { result: Integrity }) {
  const passed = result.result === "pass";
  return (
    <div className="mb-4" data-testid="integrity-result">
      <Notice
        tone={passed ? "success" : "danger"}
        title={passed ? "Integrity check passed" : "Integrity check failed"}
      >
        {passed ? (
          <p>
            All {result.checked_files} {result.checked_files === 1 ? "file matches" : "files match"}{" "}
            their recorded hashes, and all {result.checked_events} timeline entries are linked
            correctly.
          </p>
        ) : (
          <div>
            <p>
              Something no longer matches what was recorded. A hash shows a file changed after it
              was stored; it does not show who changed it or why.
            </p>
            <ul className="mt-2 list-disc pl-5">
              {result.mismatches.map((m) => (
                <li key={`${m.type}-${m.reference}-${m.detail}`}>
                  <Badge tone="danger">{m.type}</Badge> {m.reference}: {m.detail}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Notice>
    </div>
  );
}
