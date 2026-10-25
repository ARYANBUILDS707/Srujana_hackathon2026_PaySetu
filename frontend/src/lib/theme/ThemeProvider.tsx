"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore } from "react";
import type { ReactNode } from "react";

// Light / dark / system theme (DESIGN.md Section 2.3). The preference is stored on this
// device only (localStorage) and is never sent to the backend. public/theme-init.js applies
// it before the first paint; this provider keeps <html data-theme> in sync afterwards.

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "paysetu-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";
const listeners = new Set<() => void>();

function readPreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system"; // storage blocked: follow the device
  }
}

function resolve(preference: ThemePreference): ResolvedTheme {
  if (preference !== "system") return preference;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

function apply(theme: ResolvedTheme, animate: boolean) {
  const root = document.documentElement;
  if (root.dataset.theme === theme) return;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (animate && !reduced) {
    root.classList.add("theme-switching");
    window.setTimeout(() => root.classList.remove("theme-switching"), 220);
  }
  root.dataset.theme = theme;
}

function notify() {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

// A primitive snapshot ("preference:resolved") so React can compare it cheaply.
function getSnapshot(): string {
  const preference = readPreference();
  return `${preference}:${resolve(preference)}`;
}

// The server cannot know the device's theme. Hydration uses this neutral snapshot, then
// React re-renders with the real one, so the markup never mismatches.
function getServerSnapshot(): string {
  return "system:light";
}

interface ThemeValue {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  setPreference: (preference: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function useTheme(): ThemeValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside ThemeProvider");
  return value;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [preference, resolved] = snapshot.split(":") as [ThemePreference, ResolvedTheme];

  useEffect(() => {
    // Follow the device while "system" is chosen, and other tabs' changes.
    const media = window.matchMedia(DARK_QUERY);
    const sync = () => {
      apply(resolve(readPreference()), true);
      notify();
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) sync();
    };
    media.addEventListener("change", sync);
    window.addEventListener("storage", onStorage);
    apply(resolve(readPreference()), false); // in case the bootstrap script was blocked
    return () => {
      media.removeEventListener("change", sync);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable (e.g. private mode): the choice still applies until reload.
    }
    apply(resolve(next), true);
    notify();
  }, []);

  return (
    <ThemeContext.Provider value={{ preference, resolved, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}
