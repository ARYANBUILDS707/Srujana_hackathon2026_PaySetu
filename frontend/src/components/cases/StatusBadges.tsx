import { Badge, type Tone } from "@/components/ui/Badge";
import { acceptanceStateLabel, paymentStateLabel } from "@/content/app";

const acceptanceTone: Record<string, Tone> = {
  window_open: "primary",
  objection_raised: "warning",
  accepted: "success",
};

const paymentTone: Record<string, Tone> = {
  not_due: "neutral",
  overdue: "warning",
  settled: "success",
};

export function AcceptanceBadge({ state }: { state: string }) {
  return (
    <Badge tone={acceptanceTone[state] ?? "neutral"}>{acceptanceStateLabel[state] ?? state}</Badge>
  );
}

export function PaymentBadge({ state }: { state: string | null }) {
  if (!state) return <Badge>Payment date not fixed yet</Badge>;
  return <Badge tone={paymentTone[state] ?? "neutral"}>{paymentStateLabel[state] ?? state}</Badge>;
}
