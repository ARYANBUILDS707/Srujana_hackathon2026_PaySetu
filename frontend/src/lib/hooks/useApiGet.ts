"use client";

import { useCallback, useEffect, useState } from "react";
import { api, asApiError, type ApiError } from "@/lib/api/client";

interface Result<T> {
  path: string;
  data: T | null;
  error: ApiError | null;
}

/** GET a path; `null` skips the request. `reload()` refetches and keeps current data meanwhile. */
export function useApiGet<T>(path: string | null) {
  const [result, setResult] = useState<Result<T> | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let cancelled = false;
    api<T>(path)
      .then((data) => {
        if (!cancelled) setResult({ path, data, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) setResult({ path, data: null, error: asApiError(error) });
      });
    return () => {
      cancelled = true;
    };
  }, [path, tick]);

  const current = result && result.path === path ? result : null;
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: path !== null && current === null,
    reload,
  };
}
