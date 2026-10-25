import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { expect, type Page, type TestInfo } from "@playwright/test";

// Test-only placeholders, matching the e2e backend in playwright.config.ts. Never real.
export const DEMO_EMAIL = "demo@paysetu.example";
export const DEMO_PASSWORD = "e2e-only-demo-passphrase";
export const TEST_PASSWORD = "e2e-only-test-passphrase";
export const SAMPLE_BUYER = "Apex Auto Components Pvt Ltd (SAMPLE)";
export const TERMS_VERSION = "evaluation-2026-10";

/** `YYYY-MM-DD` for `days` ago, in India time (the date the backend treats as "today"). */
export function isoDaysAgo(days: number): string {
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  now.setDate(now.getDate() - days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** A unique email for this test run. */
export function uniqueEmail(testInfo: TestInfo, label = "user"): string {
  const random = Math.random().toString(36).slice(2, 8);
  return `e2e-${label}-${testInfo.project.name}-${Date.now()}-${random}@example.com`;
}

/** The CSRF headers the browser app sends (API.md 1.2), for direct API calls in tests. */
export function csrfHeaders(testInfo: TestInfo): Record<string, string> {
  return {
    Origin: new URL(String(testInfo.project.use.baseURL)).origin,
    "X-PaySetu-Client": "web",
  };
}

/**
 * Sign up a fresh supplier through the real API, confirm its email (the browser context keeps the session
 * cookie) and give it the sample buyer the delivery form expects. Each test gets its own
 * account, so tests never see each other's cases.
 */
export async function signUpWithSampleBuyer(page: Page, testInfo: TestInfo): Promise<string> {
  const email = uniqueEmail(testInfo);
  const headers = csrfHeaders(testInfo);
  const signup = await page.request.post("/api/v1/auth/signup", {
    headers,
    data: {
      full_name: "E2E Sample User",
      business_name: "E2E Sample Traders (TEST)",
      email,
      password: TEST_PASSWORD,
      accept_terms_version: TERMS_VERSION,
    },
  });
  expect(signup.status(), await signup.text()).toBe(201);
  // Phase 7A: confirm the email with the emailed link's token, as a user would.
  const link = await verificationLinkFor(email);
  const verify = await page.request.post("/api/v1/auth/verify-email", {
    headers,
    data: { token: link.split("#token=")[1] },
  });
  expect(verify.status(), await verify.text()).toBe(200);
  const buyer = await page.request.post("/api/v1/buyers", {
    headers,
    data: { legal_name: SAMPLE_BUYER },
  });
  expect(buyer.status()).toBe(201);
  return email;
}

/** Log a delivery through the real form; ends on the new case's overview page. */
export async function logDelivery(page: Page, invoice: string) {
  await page.goto("/app/cases/new");
  await expect(page.getByLabel("Buyer (required)")).toContainText("SAMPLE");
  await page.getByLabel("Invoice number (required)").fill(invoice);
  await page.getByLabel("Invoice amount (Rs) (required)").fill("500000.00");
  await page.getByLabel("Invoice date (required)").fill(isoDaysAgo(20));
  await page.getByLabel("Delivery date (required)").fill(isoDaysAgo(20));
  await page.getByRole("button", { name: "Save delivery" }).click();
  await expect(page).toHaveURL(/\/app\/cases\/[0-9a-f-]{36}$/);
}

/** Upload one evidence file through the Evidence tab (the case overview must be open). */
export async function uploadEvidence(
  page: Page,
  file: { name: string; mimeType: string; buffer: Buffer },
) {
  await page.getByRole("link", { name: "Evidence", exact: true }).first().click();
  await page.getByLabel("File (required)").setInputFiles(file);
  await page.getByRole("button", { name: "Add evidence" }).click();
  await expect(page.getByText("Evidence added and sealed")).toBeVisible();
}

/** Click "Sign out", opening the mobile menu first when the sidebar is hidden. */
export async function signOut(page: Page) {
  const menu = page.getByRole("button", { name: "Open menu" });
  if (await menu.isVisible()) await menu.click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\?reason=signed-out$/);
}

/**
 * The newest message of `kind` for `email` in the e2e backend's development outbox
 * (`EMAIL_MODE=simulated` writes `.eml` files to STORAGE_DIR/outbox; see playwright.config.ts).
 * Returns the decoded body, or null if none has arrived yet.
 */
export function readOutbox(email: string, kind: string): string | null {
  const dir = path.resolve(process.cwd(), "../backend/storage/e2e/outbox");
  if (!existsSync(dir)) return null;
  const bodies = readdirSync(dir)
    .filter((name) => name.endsWith(".eml"))
    .sort()
    .map((name) => readFileSync(path.join(dir, name), "utf8"))
    .filter((raw) => raw.includes(`To: ${email}`) && raw.includes(`X-PaySetu-Kind: ${kind}`));
  const raw = bodies.at(-1);
  if (!raw) return null;
  // Long lines are quoted-printable encoded: remove soft line breaks and decode =XX.
  return raw
    .replace(/=\r?\n/g, "")
    .replace(/=([0-9A-F]{2})/g, (_, hex: string) => String.fromCharCode(parseInt(hex, 16)));
}

/** Wait for the newest `kind` email to `email` and return its link's path + fragment. */
export async function linkFor(email: string, kind: string, route: string): Promise<string> {
  const pattern = new RegExp(`https?://[^/\\s]+(/${route}#token=[A-Za-z0-9_-]+)`);
  let link = "";
  await expect
    .poll(() => {
      const body = readOutbox(email, kind);
      const match = body ? pattern.exec(body) : null;
      link = match ? match[1] : "";
      return link;
    })
    .not.toBe("");
  return link;
}

/** Wait for a reset email and return the path + fragment of its link. */
export async function resetLinkFor(email: string): Promise<string> {
  return linkFor(email, "password_reset", "reset-password");
}

/** Wait for a verification email and return the path + fragment of its link. */
export async function verificationLinkFor(email: string): Promise<string> {
  return linkFor(email, "email_verification", "verify-email");
}
