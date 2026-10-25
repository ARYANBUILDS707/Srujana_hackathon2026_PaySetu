"use client";

import { createContext, useContext, type ReactNode } from "react";
import { ErrorState, LoadingBlock } from "@/components/ui/Notice";
import type { CaseDetail } from "@/lib/api/types";
import { useApiGet } from "@/lib/hooks/useApiGet";

interface CaseContextValue {
  caseData: CaseDetail;
  reload: () => void;
}

const CaseContext = createContext<CaseContextValue | null>(null);

export function useCase(): CaseContextValue {
  const value = useContext(CaseContext);
  if (!value) throw new Error("useCase must be used inside CaseProvider");
  return value;
}

/** Loads the case once for every tab; tabs call `reload` after they change something. */
export function CaseProvider({ caseId, children }: { caseId: string; children: ReactNode }) {
  const { data, error, reload } = useApiGet<CaseDetail>(`/cases/${encodeURIComponent(caseId)}`);
  if (error)
    return (
      <ErrorState
        message={error.status === 404 ? "This case was not found." : error.message}
        requestId={error.requestId}
        onRetry={error.status === 404 ? undefined : reload}
      />
    );
  if (!data) return <LoadingBlock label="Loading case" />;
  return <CaseContext.Provider value={{ caseData: data, reload }}>{children}</CaseContext.Provider>;
}
