import type { NextConfig } from "next";

// In development, /api/* is proxied to FastAPI so the browser sees one origin
// (ARCHITECTURE.md Section 4, ADR-004). In production the reverse proxy routes /api/*.
const apiOrigin =
  process.env.API_ORIGIN ??
  (process.env.NODE_ENV === "development" ? "http://localhost:8000" : undefined);

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
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
