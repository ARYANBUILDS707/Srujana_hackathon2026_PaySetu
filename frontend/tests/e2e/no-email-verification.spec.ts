// Email verification is no longer required (DECISIONS.md Section 12): signup and login open
// the dashboard directly, and a signed-in supplier uses its own workspace at once. Sessions
// and ownership checks are unchanged.

import { expect, test } from "@playwright/test";
import {
  csrfHeaders,
  DEMO_EMAIL,
  DEMO_PASSWORD,
  logDelivery,
  TERMS_VERSION,
  TEST_PASSWORD,
  uniqueEmail,
} from "./helpers";

test("signup and login go straight to the dashboard", async ({ page }, testInfo) => {
  const email = uniqueEmail(testInfo, "direct");
  await page.goto("/signup");
  await page.getByLabel("Your name (required)").fill("E2E Direct User");
  await page.getByLabel("Business name (required)").fill("E2E Direct Traders (TEST)");
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(TEST_PASSWORD);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Confirm your email")).toHaveCount(0);

  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("an unverified account uses its own workspace APIs; strangers stay out", async ({
  page,
  browser,
}, testInfo) => {
  const headers = csrfHeaders(testInfo);
  const response = await page.request.post("/api/v1/auth/signup", {
    headers,
    data: {
      full_name: "E2E Unverified User",
      business_name: "E2E Unverified Traders (TEST)",
      email: uniqueEmail(testInfo, "unverified"),
      password: TEST_PASSWORD,
      accept_terms_version: TERMS_VERSION,
    },
  });
  expect(response.status()).toBe(201);
  expect((await response.json()).user.email_verified).toBe(false);
  for (const path of [
    "/api/v1/cases",
    "/api/v1/buyers",
    "/api/v1/supplier",
    "/api/v1/onboarding",
  ]) {
    expect((await page.request.get(path)).status(), path).toBe(200);
  }
  const buyer = await page.request.post("/api/v1/buyers", {
    headers,
    data: { legal_name: "Sample Buyer (TEST)" },
  });
  expect(buyer.status()).toBe(201);

  // Still signed-in only, and still own data only.
  const anonymousContext = await browser.newContext({
    baseURL: String(testInfo.project.use.baseURL),
  });
  const anonymous = await anonymousContext.newPage();
  expect((await anonymous.request.get("/api/v1/cases")).status()).toBe(401);
  await anonymous.goto("/app/cases");
  await expect(anonymous).toHaveURL(/\/login\?next=%2Fapp%2Fcases$/);
  await anonymousContext.close();

  // The verification page and endpoints no longer exist.
  const verifyApi = await page.request.post("/api/v1/auth/verify-email", {
    headers,
    data: { token: "x" },
  });
  expect(verifyApi.status()).toBe(404);
  const verifyPage = await page.goto("/verify-email");
  expect(verifyPage?.status()).toBe(404);
});

test("the demo account carries on with the normal workflow", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("Email (required)").fill(DEMO_EMAIL);
  await page.getByLabel("Password (required)").fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await logDelivery(page, `E2E-DEMO-${testInfo.project.name}-${Date.now()}`);
  await expect(page.getByRole("heading", { name: /PS-\d{4}-\d{4}/ })).toBeVisible();
});
