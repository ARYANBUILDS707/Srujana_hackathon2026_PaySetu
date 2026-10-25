import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PaySetu",
  description: "Evidence-first delayed-payment protection for Indian micro and small enterprises.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // theme-init.js sets data-theme on <html> before React hydrates; suppressHydrationWarning
    // covers that one attribute (it does not affect child elements).
    <html
      lang="en-IN"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* Must block rendering: applies the saved theme before first paint (no flash).
            A same-origin static file, so no inline script and no dangerouslySetInnerHTML. */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/theme-init.js" />
      </head>
      <body className="min-h-dvh bg-canvas text-body text-ink">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
