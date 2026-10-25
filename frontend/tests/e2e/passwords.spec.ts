// Phase 6.1 in the browser: forgot and reset password (link read from the development email
// outbox), change password and sign out everywhere, against the real backend.

import { expect, test } from "@playwright/test";
import {
  csrfHeaders,
  readOutbox,
  resetLinkFor,
  signUpWithSampleBuyer,
  TEST_PASSWORD,
} from "./helpers";

const NEW_PASSWORD = "e2e-only-new-passphrase";

async function signIn(page: import("@playwright/test").Page, email: string, password: string) {
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a supplier resets a forgotten password with the emailed link", async ({ page }, testInfo) => {
  const email = await signUpWithSampleBuyer(page, testInfo);
  await page.context().clearCookies();

  await page.goto("/login");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByLabel("Email (required)").fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByTestId("forgot-done")).toContainText("If an account exists");

  const link = await resetLinkFor(email);
  await page.goto(link);
  await expect(page.getByRole("heading", { name: "Choose a new password" })).toBeVisible();
  expect(page.url()).not.toContain("token"); // removed from the address bar at once
  await page.getByLabel("New password (required)", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Confirm new password (required)").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Set new password" }).click();
  await expect(page.getByTestId("reset-done")).toContainText("every device was signed out");
  await expect(page.getByTestId("reset-done")).toContainText("We sent a confirmation");
  expect(readOutbox(email, "password_changed")).toContain("reset with an emailed link");

  await page.getByRole("link", { name: "Sign in" }).click();
  await expect(page.getByText("Your password has been reset")).toBeVisible();
  await signIn(page, email, TEST_PASSWORD);
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
  await signIn(page, email, NEW_PASSWORD);
  await expect(page).toHaveURL(/\/app$/);

  // The same link cannot be used twice.
  await page.goto(link);
  await page
    .getByLabel("New password (required)", { exact: true })
    .fill("e2e-only-third-passphrase");
  await page.getByLabel("Confirm new password (required)").fill("e2e-only-third-passphrase");
  await page.getByRole("button", { name: "Set new password" }).click();
  await expect(page.getByTestId("reset-unusable")).toContainText(
    "This reset link can no longer be used",
  );
});

test("unknown emails get the same answer and broken links explain what to do", async ({ page }) => {
  await page.goto("/forgot-password");
  await page.getByLabel("Email (required)").fill("nobody-e2e@example.com");
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByTestId("forgot-done")).toContainText("If an account exists");
  expect(readOutbox("nobody-e2e@example.com", "password_reset")).toBeNull();

  await page.goto("/reset-password");
  await expect(page.getByTestId("reset-unusable")).toContainText("incomplete");
  await page.getByRole("link", { name: "Request a new link" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);

  await page.goto("/reset-password#token=not-a-real-token");
  await page.getByLabel("New password (required)", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Confirm new password (required)").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Set new password" }).click();
  await expect(page.getByTestId("reset-unusable")).toContainText("expire after 15 minutes");
});

test("a supplier changes the password in settings and stays signed in", async ({
  page,
}, testInfo) => {
  const email = await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app/settings");
  await expect(page.getByRole("heading", { name: "Account settings" })).toBeVisible();

  await page.getByLabel("Current password (required)").fill("not-my-current-passphrase");
  await page.getByLabel("New password (required)", { exact: true }).fill(NEW_PASSWORD);
  await page.getByLabel("Confirm new password (required)").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Current password is incorrect.")).toBeVisible();

  await page.getByLabel("Current password (required)").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByTestId("password-changed")).toContainText(
    "Every other device has been signed out",
  );
  await expect(page.getByTestId("password-changed")).toContainText(email);
  expect(readOutbox(email, "password_changed")).toContain("changed from your account");

  // Still signed in on the new session.
  const me = await page.request.get("/api/v1/auth/me");
  expect(me.status()).toBe(200);
});

test("sign out everywhere ends the sessions on every device", async ({
  page,
  browser,
}, testInfo) => {
  const email = await signUpWithSampleBuyer(page, testInfo);
  const otherContext = await browser.newContext({ baseURL: String(testInfo.project.use.baseURL) });
  const other = await otherContext.newPage();
  const login = await other.request.post("/api/v1/auth/login", {
    headers: csrfHeaders(testInfo),
    data: { email, password: TEST_PASSWORD },
  });
  expect(login.status()).toBe(200);
  expect((await other.request.get("/api/v1/auth/me")).status()).toBe(200);

  await page.goto("/app/settings");
  await page.getByRole("button", { name: "Sign out everywhere" }).click();
  await page.getByRole("button", { name: "Yes, sign out on every device" }).click();
  await expect(page).toHaveURL(/\/login\?reason=signed-out-everywhere$/);
  await expect(page.getByText("You have signed out on every device.")).toBeVisible();

  expect((await other.request.get("/api/v1/auth/me")).status()).toBe(401);
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp$/);
  await otherContext.close();
});
