import type { NextConfig } from "next";

// In development, /api/* is proxied to FastAPI so the browser sees one origin
// (ARCHITECTURE.md Section 4, ADR-004). In production the reverse proxy routes /api/*.
const apiOrigin =
  process.env.API_ORIGIN ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : undefined);

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
