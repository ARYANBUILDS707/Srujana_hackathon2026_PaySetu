"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { LoadingBlock } from "@/components/ui/Notice";
import { api, SESSION_ENDED_EVENT } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";
import { loginHref } from "./redirect";

interface SessionValue {
  me: Me;
  signOut: () => Promise<void>;
  signOutEverywhere: () => Promise<void>;
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

  useEffect(() => {
    let cancelled = false;
    api<Me>("/auth/me")
      .then((current) => {
        if (!cancelled) setMe(current);
      })
      .catch(() => {
        if (!cancelled) router.replace(loginHref(window.location.pathname));
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

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

  if (!me)
    return (
      <div className="mx-auto max-w-7xl p-4 lg:p-8">
        <LoadingBlock label="Checking your session" />
      </div>
    );
  return (
    <SessionContext.Provider value={{ me, signOut, signOutEverywhere }}>
      {children}
    </SessionContext.Provider>
  );
}
