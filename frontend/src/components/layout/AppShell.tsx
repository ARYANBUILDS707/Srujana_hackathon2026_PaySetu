"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui/Icon";
import { VerificationRequired } from "@/components/account/VerificationRequired";
import { appCopy } from "@/content/app";
import { authCopy } from "@/content/auth";
import { useSession } from "@/lib/session/SessionContext";

type NavItem = { href: string; label: string; match: string; icon: IconName };

// Until the email is confirmed (Phase 7A) the workspace is replaced by the confirmation
// screen; only it and Account settings are reachable.
const unverifiedNav: NavItem[] = [
  { href: "/app", label: authCopy.verify.navVerify, match: "exact", icon: "check" },
  ...appCopy.nav.filter((item) => item.href === "/app/settings"),
];

function isActive(pathname: string, item: NavItem): boolean {
  if (item.match === "exact") return pathname === item.href;
  // "Cases" stays selected on case pages, but not on the Record delivery page.
  return (
    (pathname === item.href || pathname.startsWith(`${item.href}/`)) &&
    !pathname.startsWith("/app/cases/new")
  );
}

const sectionLabel: Record<string, string> = {
  evidence: "Evidence Vault",
  responses: "Buyer responses",
  checklist: "Case Strength",
  interest: "Interest",
  timeline: "Timeline",
};

/** Breadcrumbs come from the URL only; the case reference is shown in the page header. */
function crumbs(pathname: string): { label: string; href?: string }[] {
  const parts = pathname.split("/").filter(Boolean).slice(1); // drop "app"
  if (parts.length === 0) return [{ label: "Dashboard" }];
  if (parts[0] === "settings") return [{ label: "Account settings" }];
  if (parts[0] === "onboarding") return [{ label: "Business profile" }];
  if (parts[0] !== "cases") return [{ label: "Dashboard", href: "/app" }];
  const trail: { label: string; href?: string }[] = [{ label: "Cases", href: "/app/cases" }];
  if (parts.length === 1) return [{ label: "Cases" }];
  if (parts[1] === "new") return [...trail, { label: "Record delivery" }];
  const base = `/app/cases/${parts[1]}`;
  if (parts.length === 2) return [...trail, { label: "Case workspace" }];
  return [
    ...trail,
    { label: "Case workspace", href: base },
    { label: sectionLabel[parts[2]] ?? parts[2] },
  ];
}

function NavLink({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = isActive(pathname, item);
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className={`flex h-10 items-center gap-3 rounded-md px-3 text-body font-medium transition-colors duration-150 ${
        active
          ? "bg-surface-hover text-ink shadow-[inset_3px_0_0_var(--color-brass)]"
          : "text-ink-muted hover:bg-surface-subtle hover:text-ink"
      }`}
    >
      <Icon name={item.icon} className="size-4.5" />
      {item.label}
    </Link>
  );
}

function Wordmark() {
  return (
    <Link href="/app" className="flex items-center gap-2 text-h3 font-semibold text-primary">
      <span
        aria-hidden="true"
        className="flex size-7 items-center justify-center rounded-md bg-primary text-small text-white"
      >
        P
      </span>
      {appCopy.productName}
    </Link>
  );
}

function Account() {
  const { me, signOut } = useSession();
  const [busy, setBusy] = useState(false);
  return (
    <div className="border-t border-rule pt-4">
      <p className="truncate text-small font-medium text-ink" title={me.user.email}>
        {me.user.full_name}
      </p>
      <p className="truncate text-caption text-ink-muted" title={me.supplier.legal_name}>
        {me.supplier.legal_name}
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
  const verified = me.user.email_verified;
  const nav = verified ? appCopy.nav : unverifiedNav;
  return (
    <>
      {verified ? (
        <Link
          href={appCopy.primaryAction.href}
          className="flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-body font-medium text-white transition-colors duration-150 hover:bg-primary-hover"
        >
          <Icon name="plus" className="size-4" />
          {appCopy.primaryAction.label}
        </Link>
      ) : null}
      <nav aria-label="Main" className={`${verified ? "mt-6" : ""} flex flex-col gap-1`}>
        {nav.map((item) => (
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
      {me.supplier.legal_name}
    </span>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { me } = useSession();
  const showWorkspace = me.user.email_verified || pathname === "/app/settings";
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

  const trail = crumbs(pathname);

  return (
    <div className="min-h-dvh lg:pl-60">
      {/* Desktop sidebar: 240px */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-rule bg-surface p-4 lg:flex">
        <div className="flex h-8 items-center">
          <Wordmark />
        </div>
        <div className="mt-6">
          <SidebarBody pathname={pathname} />
        </div>
        <div className="mt-auto flex flex-col gap-4">
          <Account />
          <p className="text-caption text-ink-muted">
            Evidence preparation only. Not legal advice.
          </p>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-20 border-b border-rule bg-surface lg:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <Wordmark />
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
        {open ? (
          <div id="mobile-menu" className="border-t border-rule bg-surface p-4">
            <SidebarBody pathname={pathname} />
            <div className="mt-6">
              <Account />
            </div>
          </div>
        ) : null}
      </header>

      {/* Desktop top navigation: 64px */}
      <header className="sticky top-0 z-10 hidden h-16 items-center justify-between border-b border-rule bg-surface px-8 lg:flex">
        <nav aria-label="Breadcrumb">
          <ol className="flex items-center gap-2 text-small text-ink-muted">
            {trail.map((crumb, index) => (
              <li key={crumb.label} className="flex items-center gap-2">
                {index > 0 ? <Icon name="chevron" className="size-3.5 text-ink-faint" /> : null}
                {crumb.href ? (
                  <Link href={crumb.href} className="hover:text-ink">
                    {crumb.label}
                  </Link>
                ) : (
                  <span aria-current="page" className="font-medium text-ink">
                    {crumb.label}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </nav>
        <AccountName />
      </header>

      <div className="border-b border-warning/20 bg-warning-tint px-4 py-2 text-small text-warning lg:px-8">
        <strong className="font-semibold">{appCopy.demoBanner.title}</strong>{" "}
        {appCopy.demoBanner.body}
      </div>

      <main className="min-w-0 px-4 py-6 lg:px-8 lg:py-8">
        <div className="mx-auto w-full max-w-7xl">
          {showWorkspace ? children : <VerificationRequired />}
        </div>
        <p className="mx-auto mt-12 max-w-7xl text-caption text-ink-muted">{appCopy.disclaimer}</p>
      </main>
    </div>
  );
}
