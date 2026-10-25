"use client";

import { useParams } from "next/navigation";
import { useRef, useState, type DragEvent, type FormEvent } from "react";
import { useCase } from "@/components/cases/CaseContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { controlClass, Field } from "@/components/ui/Fields";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { HashChip } from "@/components/ui/HashChip";
import { appCopy, evidenceKindGuidance, evidenceKindLabel, uploadKinds } from "@/content/app";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { Evidence, EvidenceKind, Integrity } from "@/lib/api/types";
import { formatBytes, formatTimestamp } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

// Mirrors MAX_UPLOAD_MB (15) for an early, friendly message; the server remains the authority.
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const { reload: reloadCase } = useCase();
  const evidence = useApiGet<Evidence[]>(`/cases/${params.id}/evidence`);

  const fileInput = useRef<HTMLInputElement>(null);
  const [kind, setKind] = useState<EvidenceKind>("invoice");
  const [note, setNote] = useState("");
  const [fileName, setFileName] = useState("");
  const [localError, setLocalError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<ApiError | null>(null);
  const [justAdded, setJustAdded] = useState<Evidence | null>(null);

  const [checking, setChecking] = useState(false);
  const [integrity, setIntegrity] = useState<Integrity | null>(null);
  const [integrityError, setIntegrityError] = useState<ApiError | null>(null);

  const [dragging, setDragging] = useState(false);

  function chooseFile(files: FileList | null | undefined) {
    const picked = files?.[0];
    setFileName(picked?.name ?? "");
    setUploadError(null);
    if (picked && picked.size > MAX_UPLOAD_BYTES) {
      setLocalError(`${picked.name} is larger than 15 MB. Choose a smaller file.`);
    } else {
      setLocalError("");
    }
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    if (!fileInput.current || event.dataTransfer.files.length === 0) return;
    fileInput.current.files = event.dataTransfer.files;
    chooseFile(event.dataTransfer.files);
  }

  async function upload(event: FormEvent) {
    event.preventDefault();
    const file = fileInput.current?.files?.[0];
    if (!file) {
      setUploadError(asApiError(null));
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) return;
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
      setIntegrity(null); // a new file has not been checked yet
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
      <PageHeader
        title="Evidence Vault"
        description="Store the invoice, proof of delivery and buyer replies. Each file is kept unchanged and fingerprinted."
      />

      <Card
        title="Add evidence"
        description="Files are stored unchanged and fingerprinted with SHA-256 on the server."
      >
        <form onSubmit={upload} className="flex flex-col gap-4" noValidate>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Type of evidence" required hint={evidenceKindGuidance[kind]}>
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
          </div>
          <Field
            label="File"
            required
            error={localError || undefined}
            hint="PDF, JPEG, PNG, HEIC, email (.eml) or UTF-8 text. Up to 15 MB."
          >
            {(control) => (
              <label
                htmlFor={control.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center transition-colors duration-150 ${
                  dragging
                    ? "border-primary bg-surface-hover"
                    : "border-rule-strong bg-surface-subtle hover:bg-surface-hover"
                }`}
              >
                <Icon name="upload" className="size-6 text-ink-muted" />
                <span className="text-body font-medium text-ink">
                  {fileName ? (
                    <span className="break-all">{fileName}</span>
                  ) : (
                    "Choose a file or drop it here"
                  )}
                </span>
                <input
                  {...control}
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.heic,.eml,.txt,application/pdf,image/*,message/rfc822,text/plain"
                  onChange={(e) => chooseFile(e.target.files)}
                  className="w-full max-w-xs text-small text-ink-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-rule-strong file:bg-surface file:px-3 file:py-1.5 file:font-medium file:text-ink"
                />
              </label>
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
            <Button
              type="submit"
              loading={uploading}
              disabled={(!fileName && !uploading) || localError !== ""}
            >
              Add evidence
            </Button>
          </div>
        </form>
      </Card>

      <Card
        title="Stored evidence"
        description="Everything stored for this case, with its recorded hash."
        actions={
          <Button variant="secondary" onClick={verify} loading={checking}>
            Verify integrity
          </Button>
        }
      >
        <p className="mb-4 text-small text-ink-muted">{appCopy.shaExplainer}</p>
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
              <li key={item.id} className="grid gap-3 py-4 md:grid-cols-12 md:items-start md:gap-4">
                <div className="min-w-0 md:col-span-5">
                  <p className="break-all text-body font-medium text-ink">
                    {item.original_filename}
                  </p>
                  <p className="text-small text-ink-muted">
                    {evidenceKindLabel[item.kind]} · {formatBytes(item.size_bytes)}
                  </p>
                  {item.note ? <p className="mt-1 text-small text-ink">{item.note}</p> : null}
                </div>
                <div className="text-small text-ink-muted md:col-span-3">
                  <span className="md:hidden">Recorded </span>
                  <span className="tabular-nums">{formatTimestamp(item.received_at)}</span>
                </div>
                <div className="md:col-span-2">
                  <ItemStatus item={item} integrity={integrity} />
                </div>
                <div className="flex flex-col items-start gap-2 md:col-span-2 md:items-end">
                  <HashChip hash={item.sha256} />
                  <a
                    href={`/api/v1/evidence/${item.id}/download`}
                    className="text-small font-medium text-info hover:text-primary hover:underline"
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

/** Per-file result of the last integrity check run on this page; before that, "Not checked". */
function ItemStatus({ item, integrity }: { item: Evidence; integrity: Integrity | null }) {
  if (!integrity) return <Badge>Not checked yet</Badge>;
  const bad = integrity.mismatches.some((m) => m.reference === item.id);
  return bad ? (
    <Badge tone="danger">Hash mismatch</Badge>
  ) : (
    <Badge tone="success">Hash matches</Badge>
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
