"use client";

import { useState } from "react";
import { shortHash } from "@/lib/format";

/** Short SHA-256 with the full value one click away (DESIGN.md 5.4). */
export function HashChip({ hash, label = "SHA-256" }: { hash: string; label?: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setOpen(true); // clipboard unavailable: the full hash is shown to select by hand
    }
  }

  return (
    <span className="inline-flex flex-col gap-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`${label} hash, starts ${hash.slice(0, 8)}, ends ${hash.slice(-4)}`}
        className="inline-flex w-fit items-center gap-1 rounded-md bg-surface-subtle px-2 py-1 font-mono text-caption text-ink ring-1 ring-rule hover:bg-surface-hover"
      >
        {shortHash(hash)}
      </button>
      {open ? (
        <span className="flex flex-col gap-2 rounded-md border border-rule bg-surface p-2">
          <span className="break-all font-mono text-caption text-ink" data-testid="full-hash">
            {hash}
          </span>
          <button
            type="button"
            onClick={copy}
            className="w-fit text-small font-medium text-primary hover:text-primary-hover"
          >
            {copied ? "Copied" : "Copy hash"}
          </button>
          <span className="sr-only" role="status">
            {copied ? "Hash copied" : ""}
          </span>
        </span>
      ) : null}
    </span>
  );
}
