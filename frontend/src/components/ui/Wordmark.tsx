import Link from "next/link";

/** PaySetu mark: a charcoal tile with an orange dot (the "setu", the bridge point). */
export function Wordmark({ href }: { href: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-2 text-h3 font-semibold tracking-tight text-ink"
    >
      <span
        aria-hidden="true"
        className="relative flex size-7 items-center justify-center rounded-md bg-primary text-small font-bold text-white"
      >
        P
        <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full border-2 border-surface bg-accent" />
      </span>
      PaySetu
    </Link>
  );
}
