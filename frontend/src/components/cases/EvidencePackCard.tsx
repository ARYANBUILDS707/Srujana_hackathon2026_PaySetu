"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/components/ui/Icon";
import { HashChip } from "@/components/ui/HashChip";
import { Notice } from "@/components/ui/Notice";
import { appCopy } from "@/content/app";
import { apiDownload, asApiError, type ApiError } from "@/lib/api/client";

/** Downloads the case's evidence ZIP from the real export endpoint (read-only on the server). */
export function EvidencePackCard({ caseId }: { caseId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState<{ filename: string; packSha256: string | null } | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const file = await apiDownload(`/cases/${encodeURIComponent(caseId)}/evidence-pack`);
      const url = URL.createObjectURL(file.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDone({ filename: file.filename, packSha256: file.packSha256 });
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Evidence pack" description={appCopy.evidencePack.description} id="evidence-pack">
      <p className="text-small font-medium text-ink">The ZIP contains</p>
      <ul className="mt-1 list-disc pl-5 text-small text-ink-muted">
        {appCopy.evidencePack.contents.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <div className="mt-3">
        <Notice tone="warning" title="Demo export, not a certified document">
          {appCopy.evidencePack.notice}
        </Notice>
      </div>
      <div className="mt-4">
        <Button onClick={download} loading={busy}>
          <Icon name="download" className="size-4" />
          Download Evidence Pack
        </Button>
      </div>

      {error ? (
        <div className="mt-4" data-testid="pack-error">
          <Notice
            tone="danger"
            title={error.code === "integrity_failed" ? "Pack not created" : "Download failed"}
          >
            <p>{error.message}</p>
            {error.fieldErrors.length > 0 ? (
              <ul className="mt-2 list-disc pl-5">
                {error.fieldErrors.map((e) => (
                  <li key={`${e.field}-${e.message}`}>
                    <span className="font-mono text-caption">{e.field}</span>: {e.message}
                  </li>
                ))}
              </ul>
            ) : null}
            {error.requestId ? (
              <p className="mt-2 font-mono text-caption text-ink-muted">
                Request ID: {error.requestId}
              </p>
            ) : null}
          </Notice>
        </div>
      ) : null}

      {done ? (
        <div className="mt-4" data-testid="pack-done">
          <Notice tone="success" title="Evidence pack downloaded">
            <p>
              {done.filename} was created from the stored evidence after every file and the timeline
              passed verification.
            </p>
            {done.packSha256 ? (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="text-small text-ink-muted">
                  Pack ID (SHA-256 of manifest.json):
                </span>
                <HashChip hash={done.packSha256} label="Pack ID" />
              </div>
            ) : null}
          </Notice>
        </div>
      ) : null}
    </Card>
  );
}
