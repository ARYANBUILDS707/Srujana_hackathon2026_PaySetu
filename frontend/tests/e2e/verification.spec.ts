// Phase 7A in the browser: email verification after signup, replaced links and resend,
// the backend's refusal of unverified access, and verified users carrying on as before.

import { expect, test, type Page, type TestInfo } from "@playwright/test";
import {
  csrfHeaders,
  DEMO_EMAIL,
  DEMO_PASSWORD,
  logDelivery,
  TERMS_VERSION,
  TEST_PASSWORD,
  uniqueEmail,
  verificationLinkFor,
} from "./helpers";

/** Sign up through the API WITHOUT confirming the email; the browser keeps the session. */
async function signUpUnverified(page: Page, testInfo: TestInfo): Promise<string> {
  const email = uniqueEmail(testInfo, "unverified");
  const response = await page.request.post("/api/v1/auth/signup", {
    headers: csrfHeaders(testInfo),
    data: {
      full_name: "E2E Unverified User",
      business_name: "E2E Unverified Traders (TEST)",
      email,
      password: TEST_PASSWORD,
      accept_terms_version: TERMS_VERSION,
    },
  });
  expect(response.status()).toBe(201);
  expect((await response.json()).user.email_verified).toBe(false);
  return email;
}

test("a replaced verification link is refused, and a new one works", async ({ page }, testInfo) => {
  const email = await signUpUnverified(page, testInfo);
  const firstLink = await verificationLinkFor(email);

  await page.goto("/app");
  await expect(page.getByTestId("verification-required")).toContainText(email);
  await page.getByRole("button", { name: "Send a new link" }).click();
  await expect(page.getByText("A new link has been sent.")).toBeVisible();
  // The cooldown is shown on the button.
  await expect(page.getByRole("button", { name: /Send a new link in \d+ s/ })).toBeDisabled();

  // The first link was replaced by the resend, so it can no longer be used.
  await page.goto(firstLink);
  await page.getByRole("button", { name: "Confirm my email" }).click();
  await expect(page.getByTestId("verify-unusable")).toContainText("can no longer be used");

  let secondLink = "";
  await expect
    .poll(async () => {
      secondLink = await verificationLinkFor(email);
      return secondLink;
    })
    .not.toBe(firstLink);
  await page.goto(secondLink);
  expect(page.url()).not.toContain("token");
  await page.getByRole("button", { name: "Confirm my email" }).click();
  await expect(page.getByTestId("verify-done")).toBeVisible();
  await page.getByRole("link", { name: "Continue to PaySetu" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("an unverified user cannot use the case workspace or its APIs", async ({ page }, testInfo) => {
  await signUpUnverified(page, testInfo);
  const headers = csrfHeaders(testInfo);

  for (const path of ["/api/v1/cases", "/api/v1/buyers", "/api/v1/supplier"]) {
    const response = await page.request.get(path);
    expect(response.status(), path).toBe(403);
    expect((await response.json()).code).toBe("email_not_verified");
  }
  const create = await page.request.post("/api/v1/buyers", {
    headers,
    data: { legal_name: "Not allowed (TEST)" },
  });
  expect(create.status()).toBe(403);

  // Every workspace page shows the confirmation screen; settings stay available.
  await page.goto("/app/cases/new");
  await expect(page.getByTestId("verification-required")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save delivery" })).toHaveCount(0);
  await page.goto("/app/settings");
  await expect(page.getByRole("heading", { name: "Account settings" })).toBeVisible();
  await expect(page.getByText("Not confirmed")).toBeVisible();
});

test("a verified user carries on with the normal workflow", async ({ page }, testInfo) => {
  await page.goto("/login");
  await page.getByLabel("Email (required)").fill(DEMO_EMAIL);
  await page.getByLabel("Password (required)").fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByTestId("verification-required")).toHaveCount(0);
  await logDelivery(page, `E2E-VERIFIED-${testInfo.project.name}-${Date.now()}`);
  await expect(page.getByRole("heading", { name: /PS-\d{4}-\d{4}/ })).toBeVisible();
});
