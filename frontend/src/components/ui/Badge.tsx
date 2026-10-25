import type { ReactNode } from "react";

export type Tone = "neutral" | "primary" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-hover text-ink-muted",
  primary: "bg-info-tint text-info",
  success: "bg-success-tint text-success",
  warning: "bg-warning-tint text-warning",
  danger: "bg-danger-tint text-danger",
};

// A text label always accompanies the colour: status is never colour alone (DESIGN.md 2.2).
export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-caption ${tones[tone]}`}>
      {children}
    </span>
  );
}
