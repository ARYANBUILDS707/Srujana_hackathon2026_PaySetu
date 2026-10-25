"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { appCopy } from "@/content/app";

type NavItem = (typeof appCopy.nav)[number];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.match === "exact") return pathname === item.href;
  // "Cases" stays selected on case pages, but not on the New delivery page.
  return (
    (pathname === item.href || pathname.startsWith(`${item.href}/`)) &&
    !pathname.startsWith("/app/cases/new")
  );
}

function NavLink({
  item,
  variant,
  pathname,
}: {
  item: NavItem;
  variant: "side" | "tab";
  pathname: string;
}) {
  const active = isActive(pathname, item);
  const classes =
    variant === "side"
      ? `flex h-11 items-center rounded-md px-3 text-body font-medium ${
          active ? "bg-primary-tint text-primary" : "text-ink hover:bg-canvas"
        }`
      : `flex h-14 flex-1 items-center justify-center text-small font-medium ${
          active ? "border-t-2 border-primary text-primary" : "text-ink-muted"
        }`;
  return (
    <Link href={item.href} aria-current={active ? "page" : undefined} className={classes}>
      {item.label}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 border-b border-rule bg-surface">
        <div className="flex h-14 items-center gap-3 px-4 lg:px-6">
          <Link href="/app" className="text-h3 font-semibold text-primary">
            {appCopy.productName}
          </Link>
          <span className="hidden text-small text-ink-muted md:inline">
            Delayed-payment evidence for micro and small suppliers
          </span>
        </div>
        <div className="border-t border-rule bg-warning-tint px-4 py-2 text-small text-warning lg:px-6">
          <strong className="font-semibold">{appCopy.demoBanner.title}</strong>{" "}
          {appCopy.demoBanner.body}
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="hidden w-60 shrink-0 border-r border-rule bg-surface p-4 lg:block">
          <nav aria-label="Main" className="flex flex-col gap-1">
            {appCopy.nav.map((item) => (
              <NavLink key={item.href} item={item} variant="side" pathname={pathname} />
            ))}
          </nav>
        </aside>
        <main className="min-w-0 flex-1 px-4 py-6 pb-24 lg:px-8 lg:pb-8">
          <div className="mx-auto w-full max-w-5xl">{children}</div>
          <p className="mx-auto mt-10 max-w-5xl text-caption text-ink-muted">
            {appCopy.disclaimer}
          </p>
        </main>
      </div>

      <nav
        aria-label="Main mobile"
        className="fixed inset-x-0 bottom-0 z-10 flex border-t border-rule bg-surface lg:hidden"
      >
        {appCopy.nav.map((item) => (
          <NavLink key={item.href} item={item} variant="tab" pathname={pathname} />
        ))}
      </nav>
    </div>
  );
}
