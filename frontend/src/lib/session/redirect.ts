// Where to send the user after login. Only workspace paths are accepted, so a crafted
// `?next=` link can never redirect off-site (no open redirect).

export function safeNext(next: string | null | undefined): string {
  const inWorkspace = next === "/app" || next?.startsWith("/app/");
  if (!next || !inWorkspace || next.includes("//") || next.includes("\\")) {
    return "/app";
  }
  return next;
}

export function loginHref(from: string, reason?: "expired"): string {
  const params = new URLSearchParams({ next: safeNext(from) });
  if (reason) params.set("reason", reason);
  return `/login?${params.toString()}`;
}
