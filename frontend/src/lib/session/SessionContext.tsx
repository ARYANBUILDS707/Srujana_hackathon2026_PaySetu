"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { ErrorState, LoadingBlock } from "@/components/ui/Notice";
import { api, asApiError, SESSION_ENDED_EVENT, type ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";
import { loginHref } from "./redirect";

interface SessionValue {
  me: Me;
  signOut: () => Promise<void>;
  signOutEverywhere: () => Promise<void>;
  /** Re-reads the current user (e.g. after the email was confirmed in another tab). */
  refresh: () => Promise<Me>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

/**
 * Guards the workspace in the browser (UX only: the API authorises every request itself).
 * Loads the current user; with no valid session, or when a later request reports that the
 * session ended, it sends the user to the login page and back here afterwards.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [loadError, setLoadError] = useState<ApiError | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    api<Me>("/auth/me")
      .then((current) => {
        if (!cancelled) setMe(current);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const failure = asApiError(e);
        // Only 401 means "not signed in". A rate limit, network or server error must not
        // look like a sign-out: show it with a retry instead.
        if (failure.status === 401) router.replace(loginHref(window.location.pathname));
        else setLoadError(failure);
      });
    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  useEffect(() => {
    const onEnded = () => {
      setMe(null);
      router.replace(loginHref(window.location.pathname, "expired"));
    };
    window.addEventListener(SESSION_ENDED_EVENT, onEnded);
    return () => window.removeEventListener(SESSION_ENDED_EVENT, onEnded);
  }, [router]);

  const signOut = useCallback(async () => {
    try {
      await api<void>("/auth/logout", { method: "POST" });
    } finally {
      setMe(null);
      router.replace("/login?reason=signed-out");
    }
  }, [router]);

  const signOutEverywhere = useCallback(async () => {
    // Throws if the request fails, so the caller can show the error; on success every
    // session (including this one) is revoked and the cookie is cleared.
    await api<void>("/auth/logout-all", { method: "POST" });
    setMe(null);
    router.replace("/login?reason=signed-out-everywhere");
  }, [router]);

  const refresh = useCallback(async () => {
    const current = await api<Me>("/auth/me");
    setMe(current);
    return current;
  }, []);

  if (!me && loadError)
    return (
      <div className="mx-auto max-w-7xl p-4 lg:p-8">
        <ErrorState
          message={loadError.message}
          requestId={loadError.requestId}
          onRetry={() => {
            setLoadError(null);
            setAttempt((n) => n + 1);
          }}
        />
      </div>
    );
  if (!me)
    return (
      <div className="mx-auto max-w-7xl p-4 lg:p-8">
        <LoadingBlock label="Checking your session" />
      </div>
    );
  return (
    <SessionContext.Provider value={{ me, signOut, signOutEverywhere, refresh }}>
      {children}
    </SessionContext.Provider>
  );
}
