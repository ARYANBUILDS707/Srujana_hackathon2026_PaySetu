import { defineConfig, devices } from "@playwright/test";

const WEB_PORT = 3100;
const API_PORT = 8100;

// Viewports from DESIGN.md Section 10: 360×800 (primary mobile) and 1280×800 (desktop).
// The tests run against the REAL backend (fresh migrated + seeded SQLite database in
// backend/storage/e2e, git-ignored) behind the Next.js dev proxy. Nothing is mocked.
// Each test signs up its own account (tests/e2e/helpers.ts), so the signup rate limit is
// raised for this throwaway backend only; production refuses a raised value (app/config.py).
// The seeded demo supplier gets a login (`seed.demo_account`), used by the auth spec.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "mobile-360",
      use: { ...devices["Desktop Chrome"], viewport: { width: 360, height: 800 }, hasTouch: true },
    },
    {
      name: "desktop-1280",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: [
    {
      command:
        "rm -rf storage/e2e && .venv/bin/alembic upgrade head && .venv/bin/python -m seed.demo && " +
        ".venv/bin/python -m seed.demo_account && " +
        `.venv/bin/uvicorn app.main:create_app --factory --port ${API_PORT} --log-level warning`,
      cwd: "../backend",
      url: `http://localhost:${API_PORT}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        APP_ENV: "development",
        PUBLIC_BASE_URL: `http://localhost:${WEB_PORT}`,
        DATABASE_URL: "sqlite:///./storage/e2e/paysetu.db",
        STORAGE_DIR: "./storage/e2e",
        TOKEN_HASH_KEY: "e2e-only-token-hash-key-0123456789abcdef",
        EMAIL_MODE: "simulated",
        LOG_LEVEL: "WARNING",
        AUTH_SIGNUP_LIMIT_PER_HOUR: "200",
        DEMO_ACCOUNT_EMAIL: "demo@paysetu.example",
        DEMO_ACCOUNT_PASSWORD: "e2e-only-demo-passphrase",
      },
    },
    {
      command: `npm run dev -- --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { API_ORIGIN: `http://localhost:${API_PORT}`, NEXT_DIST_DIR: ".next-e2e" },
    },
  ],
});
