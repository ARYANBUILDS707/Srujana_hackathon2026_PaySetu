import { windowSentence } from "@/content/app";
import { daysBetween } from "@/lib/format";
import type { BuyerResponse, CaseDetail } from "@/lib/api/types";

const DAYS = Array.from({ length: 16 }, (_, day) => day);

/**
 * The DeemedClock visual (DESIGN.md 5.6): Day 0 to Day 15. The cells are decorative
 * (aria-hidden); the sentence below is the accessible description of the state.
 */
export function DayStrip({
  caseData,
  responses,
}: {
  caseData: CaseDetail;
  responses: BuyerResponse[];
}) {
  const { clock } = caseData;
  const today = clock.window_day; // null once the window has closed
  const objectionDays = new Set(
    responses
      .filter((r) => r.kind === "objection" && r.counts_as_written)
      .map((r) => daysBetween(caseData.delivery_date, r.received_on)),
  );

  return (
    <div>
      <ol aria-hidden="true" className="flex gap-1">
        {DAYS.map((day) => {
          const elapsed = today === null || day <= today;
          const isToday = today !== null && day === today;
          return (
            <li key={day} className="flex min-w-0 flex-1 flex-col items-center gap-1">
              <span
                className={`flex h-9 w-full items-center justify-center rounded-md text-caption ${
                  objectionDays.has(day)
                    ? "bg-warning-tint text-warning"
                    : elapsed
                      ? "bg-primary text-white"
                      : "bg-surface-sunken text-ink-muted"
                } ${isToday ? "outline-2 outline-offset-2 outline-primary" : ""}`}
              >
                {objectionDays.has(day) ? "!" : ""}
              </span>
              <span className="hidden text-caption text-ink-muted md:block">
                {day === 0 || day === 15 || isToday ? day : ""}
              </span>
            </li>
          );
        })}
      </ol>
      <div
        className="mt-1 hidden justify-between text-caption text-ink-muted md:flex"
        aria-hidden="true"
      >
        <span>Delivery (Day 0)</span>
        <span>Last day to object (Day 15)</span>
      </div>
      <p className="mt-3 text-body text-ink" data-testid="window-sentence">
        {windowSentence(clock)}
      </p>
    </div>
  );
}
