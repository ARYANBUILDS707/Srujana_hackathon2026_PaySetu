// The final redesign's new interactions, against the real backend: the dashboard's
// recommended next step and figures come from the API, the DeemedClock glossary, and the
// landing page's honest sample labelling.

import { expect, test } from "@playwright/test";
import { logDelivery, signUpWithSampleBuyer } from "./helpers";

test("the dashboard recommends the next step for the most urgent real case", async ({
  page,
}, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await logDelivery(page, `E2E-DASH-${testInfo.project.name}-${Date.now()}`);
  const caseId = page.url().split("/").pop() as string;
  const detail = await (await page.request.get(`/api/v1/cases/${caseId}`)).json();

  await page.goto("/app");
  const next = page.getByTestId("dashboard-next-step");
  await expect(next).toContainText("Recommended next step");
  await expect(next).toContainText(detail.reference);
  const summary = detail.checklist_summary;
  await expect(next).toContainText(`${summary.required_met} of ${summary.required_total}`);
  // The overview figures are the API's: one delivery of Rs 5,00,000.00, overdue.
  await expect(page.getByLabel("Overview")).toContainText("Rs 5,00,000.00");
  await expect(page.getByLabel("Overview")).toContainText("Cases needing attention1");

  // The single primary action goes into the case.
  await next.getByRole("link").first().click();
  await expect(page).toHaveURL(new RegExp(`/app/cases/${caseId}`));
});

test("the DeemedClock explains its terms in plain language", async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await logDelivery(page, `E2E-GLOSS-${testInfo.project.name}-${Date.now()}`);
  await page.getByText("What these terms mean").click();
  await expect(
    page.getByText(/the delivery day itself counts as the day of acceptance/),
  ).toBeVisible();
  await expect(page.getByText("never more than 45 days after acceptance")).toBeVisible();
});

test("the landing page labels sample content and has one primary hero action", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Every payment has a deadline.",
  );
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Every business deserves clarity.",
  );
  await expect(page.getByText("Sample content").first()).toBeVisible();
  await expect(
    page.getByText("An illustration of a case. Names, dates and amounts are not real."),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Open demo workspace" })).toHaveCount(1);
});

test("a temporary error during the session check is shown, not treated as a sign-out", async ({
  page,
}, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  // The one simulated response in this suite: a rate-limited session check (the real limit
  // is 300 requests per minute per user). Feature data is never mocked.
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 429,
      headers: { "content-type": "application/problem+json", "retry-after": "30" },
      body: JSON.stringify({
        code: "rate_limited",
        detail: "Too many requests. Try again shortly.",
      }),
    }),
  );
  await page.goto("/app");
  await expect(page.getByText("Too many requests. Try again shortly.")).toBeVisible();
  await expect(page).toHaveURL(/\/app$/); // not sent to the sign-in page

  await page.unroute("**/api/v1/auth/me");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});
