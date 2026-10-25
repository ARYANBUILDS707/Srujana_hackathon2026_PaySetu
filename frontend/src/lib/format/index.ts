// All money, date and hash display goes through here (DESIGN.md Section 3.3). Money arrives
// from the API as decimal strings; this only formats it for display and never calculates.

const IST = "Asia/Kolkata";

export function formatMoney(value: string | null | undefined, decimals = 0): string {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return `Rs ${number.toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** `2026-11-01` → `01 Nov 2026`. Parsed by parts, so no timezone or locale can change it. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  if (!year || !month || !day) return iso;
  return `${String(day).padStart(2, "0")} ${MONTHS[month - 1]} ${year}`;
}

/** UTC ISO timestamp → `01 Nov 2026, 14:32 IST`. */
export function formatTimestamp(iso: string): string {
  const instant = new Date(iso);
  if (Number.isNaN(instant.getTime())) return iso;
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: IST,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(instant)
      .map((part) => [part.type, part.value]),
  );
  const date = formatDate(`${parts.year}-${parts.month}-${parts.day}`);
  return `${date}, ${parts.hour}:${parts.minute} IST`;
}

/** Today's calendar date in India as `YYYY-MM-DD` (used only to pre-fill a form). */
export function todayInIndia(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: IST });
}

/** Whole days from `fromIso` to `toIso` (both `YYYY-MM-DD`). */
export function daysBetween(fromIso: string, toIso: string): number {
  const toUtc = (iso: string) => {
    const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((toUtc(toIso) - toUtc(fromIso)) / 86_400_000);
}

export function shortHash(hash: string): string {
  return hash.length > 14 ? `${hash.slice(0, 8)}…${hash.slice(-4)}` : hash;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Adds decimal-string amounts exactly (in paise, with BigInt) for display totals such as the
 * principal tracked across cases. Not a legal calculation: it only totals what the API returned.
 */
export function sumMoney(values: string[]): string {
  let paise = BigInt(0);
  for (const value of values) {
    const [whole, fraction = ""] = value.split(".");
    const cents = BigInt(`${whole}${fraction.padEnd(2, "0").slice(0, 2)}`);
    paise += cents;
  }
  const text = paise.toString().padStart(3, "0");
  return `${text.slice(0, -2)}.${text.slice(-2)}`;
}
