import type { NextConfig } from "next";

// In development, /api/* is proxied to FastAPI so the browser sees one origin
// (ARCHITECTURE.md Section 4, ADR-004). In production the reverse proxy routes /api/*.
const apiOrigin = (
  process.env.API_ORIGIN ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : undefined)
)?.replace(/\/+$/, "");

// The rewrite below is fixed at BUILD time. A Vercel build without API_ORIGIN used to succeed and
// then answer every /api/* call with a 404 page (the browser showed "The request failed."), so
// fail the deployment loudly instead. Only Vercel builds are checked (Vercel sets VERCEL=1);
// local builds, tests and other hosts are unchanged.
if (process.env.VERCEL === "1" && !apiOrigin) {
  throw new Error(
    "API_ORIGIN is not set. In the Vercel project settings add API_ORIGIN (the API's https " +
      "origin, no trailing slash), then redeploy.",
  );
}

const nextConfig: NextConfig = {
  // Playwright sets its own build directory, so e2e runs can coexist with a developer's
  // `next dev` (Next.js locks the build directory per server).
  distDir: process.env.NEXT_DIST_DIR || ".next",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    if (!apiOrigin) {
      return [];
    }
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
