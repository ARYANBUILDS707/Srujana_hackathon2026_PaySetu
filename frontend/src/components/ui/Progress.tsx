/** A readiness bar. The value comes from the API; the bar only draws it. */
export function Progress({ value, max, label }: { value: number; max: number; label: string }) {
  const percent = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className="h-2 w-full overflow-hidden rounded-full bg-surface-hover"
    >
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-200 ease-standard"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}
