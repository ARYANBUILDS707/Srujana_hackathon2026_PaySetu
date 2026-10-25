import type { ReactNode } from "react";

export type Tone = "neutral" | "primary" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-sunken text-ink-muted",
  primary: "bg-primary-tint text-primary-hover",
  success: "bg-success-tint text-success",
  warning: "bg-warning-tint text-warning",
  danger: "bg-danger-tint text-danger",
};

// A text label always accompanies the colour: status is never colour alone (DESIGN.md 2.2).
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-caption ${tones[tone]}`}>
      {children}
    </span>
  );
}
