"use client";

import { Icon } from "@/components/ui/Icon";
import { useTheme } from "@/lib/theme/ThemeProvider";

/** Sun/Moon button: switches between light and dark (an explicit choice, saved locally). */
export function ThemeToggle() {
  const { resolved, setPreference } = useTheme();
  const dark = resolved === "dark";
  return (
    <button
      type="button"
      onClick={() => setPreference(dark ? "light" : "dark")}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Switch to light theme" : "Switch to dark theme"}
      data-testid="theme-toggle"
      className="flex size-11 items-center justify-center rounded-md text-ink-muted transition-colors duration-150 hover:bg-surface-hover hover:text-ink lg:size-10"
    >
      <Icon name={dark ? "sun" : "moon"} className="size-5" />
    </button>
  );
}
