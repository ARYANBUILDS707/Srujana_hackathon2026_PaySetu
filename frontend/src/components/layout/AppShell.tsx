"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui/Icon";
import { LoadingBlock } from "@/components/ui/Notice";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { Wordmark } from "@/components/ui/Wordmark";
import { appCopy } from "@/content/app";
import type { Me } from "@/lib/api/types";
import { useSession } from "@/lib/session/SessionContext";

type NavItem = { href: string; label: string; match: string; icon: IconName };

/** Navigation for the signed-in roles (UX only: the API authorises every request). */
function navFor(me: Me): NavItem[] {
  const reviewer = me.roles.includes("reviewer");
  if (!me.supplier) return [appCopy.reviewNav, appCopy.nav[appCopy.nav.length - 1]];
  if (!reviewer) return appCopy.nav;
  return [...appCopy.nav.slice(0, -1), appCopy.reviewNav, appCopy.nav[appCopy.nav.length - 1]];
}

/** Pages a reviewer-only staff account (no supplier workspace) can use. */
function staffPage(pathname: string): boolean {
  return pathname.startsWith("/app/review") || pathname === "/app/settings";
}

function isActive(pathname: string, item: NavItem): boolean {
  if (item.match === "exact") return pathname === item.href;
  // "Cases" stays selected on case pages, but not on the Record delivery page.
  return (
    (pathname === item.href || pathname.startsWith(`${item.href}/`)) &&
    !pathname.startsWith("/app/cases/new")
  );
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = isActive(pathname, item);
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`flex h-10 items-center gap-3 rounded-md px-3 text-body font-medium transition-colors duration-150 ${
        active
          ? "bg-surface-subtle font-semibold text-ink shadow-[inset_3px_0_0_var(--color-accent)]"
          : "text-ink-muted hover:bg-surface-subtle hover:text-ink"
      }`}
    >
      <Icon name={item.icon} className="size-4.5" />
      {item.label}
    </Link>
  );
}

function AppWordmark() {
  return <Wordmark href="/app" />;
}

function Account() {
  const { me, signOut } = useSession();
  const [busy, setBusy] = useState(false);
  return (
    <div className="border-t border-rule pt-4">
      <p className="truncate text-small font-medium text-ink" title={me.user.email}>
        {me.user.full_name}
      </p>
      <p className="truncate text-caption text-ink-muted">
        {me.supplier?.legal_name ?? appCopy.reviewerAccountLabel}
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={() => {
          setBusy(true);
          void signOut();
        }}
        className="mt-3 flex h-10 w-full items-center justify-center rounded-md border border-control text-small font-medium text-ink transition-colors duration-150 hover:bg-surface-subtle disabled:opacity-60"
      >
        {busy ? "Signing out…" : "Sign out"}
      </button>
    </div>
  );
}

function SidebarBody({ pathname }: { pathname: string }) {
  const { me } = useSession();
  return (
    <>
      {me.supplier ? (
        <Link
          href={appCopy.primaryAction.href}
          className="flex h-10 items-center justify-center gap-2 rounded-md border border-rule-strong bg-surface px-4 text-body font-medium text-ink transition-colors duration-150 hover:border-ink hover:bg-surface-subtle"
        >
          <Icon name="plus" className="size-4" />
          {appCopy.primaryAction.label}
        </Link>
      ) : null}
      <nav aria-label="Main" className={`${me.supplier ? "mt-6 " : ""}flex flex-col gap-1`}>
        {navFor(me).map((item) => (
          <NavLink key={item.href} item={item} pathname={pathname} />
        ))}
      </nav>
    </>
  );
}

function AccountName() {
  const { me } = useSession();
  return (
    <span className="max-w-xs truncate text-small text-ink-muted" title={me.user.email}>
      {me.supplier?.legal_name ?? appCopy.reviewerAccountLabel}
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me } = useSession();
  // A reviewer-only staff account has no supplier workspace (the API answers it 403).
  const misplaced = !me.supplier && !staffPage(pathname);
  useEffect(() => {
    if (misplaced) router.replace(appCopy.reviewNav.href);
  }, [misplaced, router]);
  const [menu, setMenu] = useState({ open: false, path: pathname });
  const open = menu.open && menu.path === pathname; // navigating closes the menu

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenu({ open: false, path: pathname });
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, pathname]);

  // Only the dashboard carries the short disclaimer line.
  const isDashboard = pathname === "/app";

  return (
    <div className="min-h-dvh lg:pl-60">
      {/* Desktop sidebar: 240px */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-rule bg-surface p-4 lg:flex">
        <div className="flex h-8 items-center">
          <AppWordmark />
        </div>
        <div className="mt-6">
          <SidebarBody pathname={pathname} />
        </div>
        <div className="mt-auto">
          <Account />
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 border-b border-rule bg-surface lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <AppWordmark />
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              type="button"
              aria-expanded={open}
              aria-controls="mobile-menu"
              aria-label={open ? "Close menu" : "Open menu"}
              onClick={() => setMenu({ open: !open, path: pathname })}
              className="flex size-11 items-center justify-center rounded-md text-ink hover:bg-surface-hover"
            >
              <Icon name={open ? "close" : "menu"} />
            </button>
          </div>
        </div>
        {open ? (
          <div id="mobile-menu" className="border-t border-rule bg-surface p-4">
            <SidebarBody pathname={pathname} />
            <div className="mt-6">
              <Account />
            </div>
          </div>
        ) : null}
      </header>

      {/* Desktop top bar: 64px */}
      <header className="sticky top-0 z-10 hidden h-16 items-center justify-end border-b border-rule bg-surface px-8 lg:flex">
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <AccountName />
        </div>
      </header>

      <main className="min-w-0 px-4 py-6 lg:px-8 lg:py-8">
        <div className="mx-auto w-full max-w-7xl">
          {misplaced ? <LoadingBlock label="Opening the review queue" /> : children}
        </div>
        {isDashboard ? (
          <p className="mx-auto mt-12 max-w-7xl text-caption text-ink-muted">
            {appCopy.shortDisclaimer}
          </p>
        ) : null}
      </main>
    </div>
  );
}
