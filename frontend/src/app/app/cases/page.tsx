"use client";

import { useState } from "react";
import { CaseRows } from "@/components/cases/CaseRows";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { controlClass, Field } from "@/components/ui/Fields";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/Notice";
import type { CaseSummary } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

export default function CasesPage() {
  const { data, error, loading, reload } = useApiGet<CaseSummary[]>("/cases?limit=100");
  const [query, setQuery] = useState("");

  const needle = query.trim().toLowerCase();
  const visible = (data ?? []).filter(
    (c) =>
      !needle ||
      c.invoice_number.toLowerCase().includes(needle) ||
      c.buyer.legal_name.toLowerCase().includes(needle) ||
      c.reference.toLowerCase().includes(needle),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-h1 text-ink">Cases</h1>
        <ButtonLink href="/app/cases/new">Log a delivery</ButtonLink>
      </div>

      {error ? (
        <ErrorState message={error.message} requestId={error.requestId} onRetry={reload} />
      ) : loading ? (
        <LoadingBlock label="Loading cases" />
      ) : (data ?? []).length === 0 ? (
        <EmptyState
          title="No deliveries yet"
          body="Log your first delivery to start the 15-day objection window."
          action={<ButtonLink href="/app/cases/new">Log a delivery</ButtonLink>}
        />
      ) : (
        <Card>
          <div className="mb-4 max-w-sm">
            <Field label="Search by invoice, buyer or reference">
              {(control) => (
                <input
                  {...control}
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className={controlClass}
                />
              )}
            </Field>
          </div>
          {visible.length === 0 ? (
            <p className="text-small text-ink-muted">No cases match this search.</p>
          ) : (
            <CaseRows cases={visible} />
          )}
        </Card>
      )}
    </div>
  );
}
