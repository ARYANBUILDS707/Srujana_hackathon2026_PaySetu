"use client";

import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useCase } from "@/components/cases/CaseContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field, textareaClass } from "@/components/ui/Fields";
import { EmptyState, ErrorState, LoadingBlock, Notice } from "@/components/ui/Notice";
import { responseChannelLabel, responseKindLabel } from "@/content/app";
import { api, asApiError, type ApiError } from "@/lib/api/client";
import type { BuyerResponse, ResponseChannel, ResponseKind } from "@/lib/api/types";
import { formatDate, todayInIndia } from "@/lib/format";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function ResponsesPage() {
  const params = useParams<{ id: string }>();
  const { caseData, reload: reloadCase } = useCase();
  const responses = useApiGet<BuyerResponse[]>(`/cases/${params.id}/responses`);

  const [kind, setKind] = useState<ResponseKind>("objection");
  const [channel, setChannel] = useState<ResponseChannel>("email");
  const [receivedOn, setReceivedOn] = useState(todayInIndia());
  const [summary, setSummary] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const [removalDate, setRemovalDate] = useState(todayInIndia());
  const [removeError, setRemoveError] = useState<ApiError | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api<BuyerResponse[]>(`/cases/${params.id}/responses`, {
        method: "POST",
        json: { kind, channel, received_on: receivedOn, summary },
      });
      setSummary("");
      responses.reload();
      reloadCase();
    } catch (e) {
      setError(asApiError(e));
    } finally {
      setSaving(false);
    }
  }

  async function removeObjection(responseId: string) {
    setRemoveError(null);
    try {
      await api<BuyerResponse[]>(`/cases/${params.id}/responses/${responseId}/remove-objection`, {
        method: "POST",
        json: { removed_on: removalDate },
      });
      responses.reload();
      reloadCase();
    } catch (e) {
      setRemoveError(asApiError(e));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card
        title="Record a buyer response"
        description={`Only a written objection received by Day 15 (${formatDate(caseData.clock.window_end)}) changes the acceptance date.`}
      >
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Type of reply" required error={error?.forField("kind")}>
              {(control) => (
                <select
                  {...control}
                  value={kind}
                  onChange={(e) => setKind(e.target.value as ResponseKind)}
                  className={controlClass}
                >
                  {(Object.keys(responseKindLabel) as ResponseKind[]).map((k) => (
                    <option key={k} value={k}>
                      {responseKindLabel[k]}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <Field label="How it arrived" required error={error?.forField("channel")}>
              {(control) => (
                <select
                  {...control}
                  value={channel}
                  onChange={(e) => setChannel(e.target.value as ResponseChannel)}
                  className={controlClass}
                >
                  {(Object.keys(responseChannelLabel) as ResponseChannel[]).map((c) => (
                    <option key={c} value={c}>
                      {responseChannelLabel[c]}
                    </option>
                  ))}
                </select>
              )}
            </Field>
            <Field label="Date received" required error={error?.forField("received_on")}>
              {(control) => (
                <input
                  {...control}
                  type="date"
                  value={receivedOn}
                  max={todayInIndia()}
                  onChange={(e) => setReceivedOn(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
          </div>
          <Field label="What the buyer said" required error={error?.forField("summary")}>
            {(control) => (
              <textarea
                {...control}
                value={summary}
                maxLength={1000}
                onChange={(e) => setSummary(e.target.value)}
                className={textareaClass}
              />
            )}
          </Field>
          {error && error.fieldErrors.length === 0 ? (
            <Notice tone="danger" title="This reply was not saved">
              {error.message}
            </Notice>
          ) : null}
          <div>
            <Button type="submit" loading={saving} disabled={!summary.trim()}>
              Save response
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Responses">
        {removeError ? (
          <div className="mb-4">
            <Notice tone="danger">{removeError.message}</Notice>
          </div>
        ) : null}
        {responses.error ? (
          <ErrorState
            message={responses.error.message}
            requestId={responses.error.requestId}
            onRetry={responses.reload}
          />
        ) : responses.loading ? (
          <LoadingBlock label="Loading responses" />
        ) : (responses.data ?? []).length === 0 ? (
          <EmptyState
            title="No buyer responses recorded"
            body="If the buyer replies, record it here so the clock reflects it."
          />
        ) : (
          <ul className="divide-y divide-rule" data-testid="response-list">
            {responses.data?.map((r) => (
              <li key={r.id} className="py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-body font-medium text-ink">
                    {responseKindLabel[r.kind]}
                  </span>
                  <Badge>{responseChannelLabel[r.channel]}</Badge>
                  {r.affects_acceptance ? <Badge tone="warning">Affects acceptance</Badge> : null}
                  {r.objection_removed_on ? (
                    <Badge tone="success">Removed {formatDate(r.objection_removed_on)}</Badge>
                  ) : null}
                </div>
                <p className="mt-1 text-small text-ink-muted">
                  Received {formatDate(r.received_on)}
                </p>
                <p className="mt-1 text-body text-ink">{r.summary}</p>
                <p className="mt-1 text-small text-ink-muted">{r.note}</p>
                {r.kind === "objection" && !r.objection_removed_on && r.affects_acceptance ? (
                  <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md bg-canvas p-3">
                    <Field label="Date the objection was removed">
                      {(control) => (
                        <input
                          {...control}
                          type="date"
                          value={removalDate}
                          max={todayInIndia()}
                          onChange={(e) => setRemovalDate(e.target.value)}
                          className={controlClass}
                        />
                      )}
                    </Field>
                    <Button variant="secondary" onClick={() => removeObjection(r.id)}>
                      Mark objection removed
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
