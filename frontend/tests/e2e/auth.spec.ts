// Phase 6 in the browser: sign-up, sign-in, sign-out, protected pages, sessions that end
// mid-use and cross-supplier isolation, against the real backend.

import { expect, test } from "@playwright/test";
import {
  csrfHeaders,
  DEMO_EMAIL,
  DEMO_PASSWORD,
  logDelivery,
  signOut,
  signUpWithSampleBuyer,
  TEST_PASSWORD,
  uniqueEmail,
} from "./helpers";

async function fillSignup(
  page: import("@playwright/test").Page,
  email: string,
  password = TEST_PASSWORD,
) {
  await page.getByLabel("Your name (required)").fill("E2E Sample User");
  await page.getByLabel("Business name (required)").fill("E2E Signup Traders (TEST)");
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(password);
  await page.getByRole("checkbox").check();
}

test("the workspace sends signed-out visitors to the login page", async ({ page }) => {
  await page.goto("/app/cases");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fcases$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("a supplier signs up, uses the workspace, signs out and signs back in", async ({
  page,
}, testInfo) => {
  const email = uniqueEmail(testInfo, "signup");
  await page.goto("/signup");
  await fillSignup(page, email);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("main")).toContainText("E2E Signup Traders (TEST)");
  await expect(page.getByText("Record your first delivery")).toBeVisible();

  await signOut(page);
  await expect(page.getByText("You have signed out.")).toBeVisible();
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp$/);

  await page.getByLabel("Email (required)").fill(email.toUpperCase());
  await page.getByLabel("Password (required)").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test("sign-up and sign-in errors are shown without losing the form", async ({ page }, testInfo) => {
  const email = await signUpWithSampleBuyer(page, testInfo);
  await page.context().clearCookies();

  await page.goto("/signup");
  await fillSignup(page, email);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Could not create an account with these details.")).toBeVisible();
  await expect(page.getByLabel("Email (required)")).toHaveValue(email);

  await fillSignup(page, uniqueEmail(testInfo, "common"), "Password123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("This password is too common")).toBeVisible();

  await page.goto("/login");
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill("not-the-right-passphrase");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test("signing in returns to the requested page but never to another site", async ({
  page,
}, testInfo) => {
  const email = await signUpWithSampleBuyer(page, testInfo);
  await page.context().clearCookies();

  await page.goto("/login?next=https://evil.example/");
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/localhost:\d+\/app$/);

  await page.context().clearCookies();
  await page.goto("/app/cases/new");
  await expect(page).toHaveURL(/next=%2Fapp%2Fcases%2Fnew/);
  await page.getByLabel("Email (required)").fill(email);
  await page.getByLabel("Password (required)").fill(TEST_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app\/cases\/new$/);
});

test("a session that ends mid-use sends the user to sign in again", async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // The session is revoked elsewhere (e.g. signed out in another tab).
  const out = await page.request.post("/api/v1/auth/logout", { headers: csrfHeaders(testInfo) });
  expect(out.status()).toBe(204);

  await page.goto("/app/cases");
  await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fcases/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("an expired session during client navigation explains why", async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  // Replace the session cookie with one the server does not know (expired or revoked).
  const [cookie] = (await page.context().cookies()).filter((c) => c.name === "ps_session");
  expect(cookie.httpOnly).toBe(true);
  expect(cookie.sameSite).toBe("Lax");
  await page.context().addCookies([{ ...cookie, value: "expired-session-token" }]);

  // A client-side navigation: the next API call gets 401 and the app reacts to it.
  await page.getByRole("main").getByRole("link", { name: "Record delivery" }).first().click();
  await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fcases%2Fnew&reason=expired$/);
  await expect(page.getByText("Your session has ended. Sign in again to continue.")).toBeVisible();
});

test("a supplier cannot open another supplier's case, evidence or pack", async ({
  page,
  browser,
}, testInfo) => {
  // Supplier A: the seeded demo account, in its own browser context.
  const ownerContext = await browser.newContext({ baseURL: String(testInfo.project.use.baseURL) });
  const owner = await ownerContext.newPage();
  await owner.goto("/login");
  await owner.getByLabel("Email (required)").fill(DEMO_EMAIL);
  await owner.getByLabel("Password (required)").fill(DEMO_PASSWORD);
  await owner.getByRole("button", { name: "Sign in" }).click();
  await expect(owner).toHaveURL(/\/app$/);
  const me = await (await owner.request.get("/api/v1/auth/me")).json();
  expect(me.supplier).toMatchObject({
    legal_name: "Ravi Fasteners (DEMO - synthetic data)",
    demo_mode: true,
  });
  await logDelivery(owner, `E2E-OWNER-${testInfo.project.name}-${Date.now()}`);
  const caseUrl = new URL(owner.url()).pathname;
  const caseId = caseUrl.split("/").pop() as string;

  // Supplier B: a new account trying A's case by URL and by direct API calls.
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto(caseUrl);
  await expect(page.getByText("This case was not found.")).toBeVisible();
  for (const path of [
    `/api/v1/cases/${caseId}`,
    `/api/v1/cases/${caseId}/evidence`,
    `/api/v1/cases/${caseId}/timeline`,
    `/api/v1/cases/${caseId}/evidence-pack`,
  ]) {
    const response = await page.request.get(path);
    expect(response.status(), path).toBe(404);
  }
  const write = await page.request.post(`/api/v1/cases/${caseId}/integrity-check`, {
    headers: csrfHeaders(testInfo),
  });
  expect(write.status()).toBe(404);

  // A still sees the case; B's attempts recorded nothing on it.
  const timeline = await owner.request.get(`/api/v1/cases/${caseId}/timeline`);
  expect((await timeline.json()).map((e: { event_type: string }) => e.event_type)).toEqual([
    "case_created",
  ]);
  await ownerContext.close();
});
