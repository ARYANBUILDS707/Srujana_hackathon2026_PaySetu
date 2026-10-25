import type { Metadata } from "next";
import type { ReactNode } from "react";

// The reset token arrives in the URL fragment, which browsers never send to servers. As a
// second guard, this page sends no Referer at all.
export const metadata: Metadata = { referrer: "no-referrer" };

export default function ResetPasswordLayout({ children }: { children: ReactNode }) {
  return children;
}
