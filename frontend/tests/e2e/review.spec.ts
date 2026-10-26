// Phase 7C in the browser: the reviewer queue, manual checks, decisions with reasons, the
// supplier's view of them, resubmission after a request for information, and role boundaries.
// The reviewer session comes from global-setup.ts (one login for the run).

import { expect, test, type Browser, type Page, type TestInfo } from "@playwright/test";
import { csrfHeaders, REVIEWER_STATE, signUpWithSampleBuyer } from "./helpers";

test.use({ storageState: REVIEWER_STATE });

function pdf(label: string): Buffer {
  return Buffer.from(
    `%PDF-1.4\n% SAMPLE e2e review certificate ${label}, not a real document\n` +
      "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
      "2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n" +
      "xref\n0 3\ntrailer<</Root 1 0 R/Size 3>>\nstartxref\n9\n%%EOF\n",
  );
}

function uniqueUdyam(): string {
  const digits = String(Math.floor(Math.random() * 10_000_000)).padStart(7, "0");
  return `UDYAM-GJ-07-${digits}`;
}

/** A separate, signed-out browser context for the supplier (the page fixture is the reviewer). */
async function supplierPage(browser: Browser, testInfo: TestInfo): Promise<Page> {
  const context = await browser.newContext({
    baseURL: testInfo.project.use.baseURL,
    viewport: testInfo.project.use.viewport,
    storageState: { cookies: [], origins: [] },
  });
  return context.newPage();
}

/** Sign a supplier up and submit complete onboarding details through the real API. */
async function submitBusiness(page: Page, testInfo: TestInfo, name: string, udyam: string) {
  await signUpWithSampleBuyer(page, testInfo);
  const headers = csrfHeaders(testInfo);
  const draft = await page.request.put("/api/v1/onboarding/draft", {
    headers,
    data: {
      enterprise_name: name,
      udyam_number: udyam,
      enterprise_class: "micro",
      address_line1: "Plot 7, Sample Industrial Estate",
      city: "Surat",
      state: "Gujarat",
      pin_code: "395003",
      contact_email: "accounts@sample.example",
      representative_name: "Sample Proprietor",
      representative_role: "proprietor",
      authority_confirmed: true,
    },
  });
  expect(draft.status(), await draft.text()).toBe(200);
  const upload = await page.request.post("/api/v1/onboarding/certificate", {
    headers,
    multipart: {
      file: { name: "udyam.pdf", mimeType: "application/pdf", buffer: pdf(name) },
    },
  });
  expect(upload.status()).toBe(201);
  const submit = await page.request.post("/api/v1/onboarding/submit", { headers });
  expect(submit.status()).toBe(200);
}

async function latestSubmissionId(page: Page): Promise<string> {
  const onboarding = await (await page.request.get("/api/v1/onboarding")).json();
  return onboarding.submissions[0].id as string;
}

async function decide(page: Page, option: string, reason: string, note?: string) {
  const form = page.getByTestId("decision-form");
  await form.getByRole("radio", { name: option }).check();
  await form.getByLabel("Reason (required)").fill(reason);
  if (note) await form.getByLabel("Internal note (optional)").fill(note);
  await form.getByRole("button", { name: "Record decision" }).click();
  await form.getByRole("button", { name: "Confirm" }).click();
}

test("a reviewer requests information, the supplier resubmits, and the reviewer approves", async ({
  page,
  browser,
}, testInfo) => {
  test.setTimeout(120_000); // a two-submission journey across two browser contexts
  const name = `E2E Review Works ${testInfo.project.name} (TEST)`;
  const supplier = await supplierPage(browser, testInfo);
  await submitBusiness(supplier, testInfo, name, uniqueUdyam());
  const firstId = await latestSubmissionId(supplier);

  // The queue lists it (API-checked, because other specs' submissions share the queue).
  await page.goto("/app/review");
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  await expect(page.getByText("not a government verification")).toBeVisible();
  const queue = await (await page.request.get("/api/v1/review/submissions?limit=100")).json();
  expect(queue.items.map((i: { submission_id: string }) => i.submission_id)).toContain(firstId);

  // Detail: supplier-submitted only, frozen snapshot, certificate as a download.
  await page.goto(`/app/review/${firstId}`);
  await expect(page.getByRole("heading", { name })).toBeVisible();
  await expect(page.getByTestId("evidence-level")).toContainText("Supplier-submitted only");
  await expect(page.getByTestId("submitted-details")).toContainText("Surat, Gujarat, 395003");
  await expect(page.getByText("The stored snapshot matches its fingerprint.")).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("review-certificate-download").click(),
  ]);
  expect(download.suggestedFilename()).toBe("udyam.pdf");
  await expect(page.getByText("Approval is not available yet")).toBeVisible();
  await expect(page.getByRole("radio", { name: "Approve" })).toBeDisabled();

  // A certificate-only check, then a request for information.
  const check = page.getByTestId("check-form");
  await check.getByLabel("Source consulted (required)").selectOption("certificate_only");
  await check
    .getByLabel("What exactly you consulted (required)")
    .fill("The uploaded certificate PDF, page 1 only");
  await check.getByLabel("Result: Registered address").selectOption("not_found");
  await check.getByRole("button", { name: "Record check" }).click();
  await expect(page.getByText("Check recorded.")).toBeVisible();
  await expect(page.getByTestId("evidence-level")).toContainText("Manually reviewed");
  await expect(page.getByTestId("review-checks")).toContainText("Uploaded certificate only");
  const reason = "Upload the full certificate including the address page.";
  await decide(page, "Request more information", reason, "INTERNAL e2e note for reviewers");
  await expect(page.getByTestId("review-decision")).toContainText("Needs information");
  await expect(page.getByTestId("review-status")).toContainText("Needs information");

  // The supplier sees the reason (not the internal note), corrects and submits again.
  await supplier.goto("/app/onboarding");
  await expect(supplier.getByTestId("review-outcome")).toContainText(reason);
  await expect(supplier.getByText("INTERNAL e2e note")).toHaveCount(0);
  await supplier.getByLabel("Address line 2").fill("Gate 2");
  await supplier.getByRole("button", { name: "Review & submit" }).click();
  await supplier.getByRole("button", { name: "Submit for review" }).click();
  await expect(supplier.getByTestId("onboarding-submitted")).toContainText("Submitted for review");
  await expect(supplier.getByTestId("submission-history")).toContainText("Needs information");
  await expect(supplier.getByTestId("submission-history")).toContainText("Awaiting review");
  const secondId = await latestSubmissionId(supplier);
  expect(secondId).not.toBe(firstId);

  // The new submission: a portal check where number and name match, then approval.
  await page.goto(`/app/review/${secondId}`);
  await expect(page.getByTestId("review-history")).toContainText("Submission 1");
  await expect(page.getByTestId("submitted-details")).toContainText("Gate 2");
  const udyam = (await (await supplier.request.get("/api/v1/onboarding")).json()).udyam_number;
  await check
    .getByLabel("What exactly you consulted (required)")
    .fill("Udyam portal, Print / Verify page, searched by number");
  await check.getByLabel("Result: Udyam Registration Number").selectOption("match");
  await check.getByLabel("What you saw at the source: Udyam Registration Number").fill(udyam);
  await check.getByLabel("Result: Enterprise name").selectOption("match");
  await check.getByLabel("What you saw at the source: Enterprise name").fill(name);
  await check.getByRole("button", { name: "Record check" }).click();
  await expect(page.getByTestId("evidence-level")).toContainText(
    "Matched an official record (manual check)",
  );
  await decide(page, "Approve", "Number and name matched on the portal by manual lookup.");
  await expect(page.getByTestId("review-status")).toContainText("Approved");
  await expect(page.getByTestId("decision-form")).toHaveCount(0);

  // The decision is final for everyone.
  const again = await page.request.post(`/api/v1/review/submissions/${secondId}/decision`, {
    headers: csrfHeaders(testInfo),
    data: { decision: "REJECTED", reason: "Trying to change a final decision." },
  });
  expect(again.status()).toBe(409);
  await supplier.goto("/app/onboarding");
  await expect(supplier.getByTestId("review-outcome")).toContainText(
    "Approved by a PaySetu reviewer",
  );
  await expect(supplier.getByTestId("review-outcome")).toContainText(
    "not a government verification",
  );
  const edit = await supplier.request.put("/api/v1/onboarding/draft", {
    headers: csrfHeaders(testInfo),
    data: { enterprise_name: "Changed after approval" },
  });
  expect(edit.status()).toBe(409);
  await supplier.context().close();
});

test("suppliers cannot use the review queue", async ({ browser }, testInfo) => {
  const supplier = await supplierPage(browser, testInfo);
  await submitBusiness(supplier, testInfo, "E2E No Access (TEST)", uniqueUdyam());
  const id = await latestSubmissionId(supplier);
  for (const path of ["/api/v1/review/submissions", `/api/v1/review/submissions/${id}`]) {
    const response = await supplier.request.get(path);
    expect(response.status()).toBe(403);
  }
  const certificate = await supplier.request.get(`/api/v1/review/submissions/${id}/certificate`);
  expect(certificate.status()).toBe(403);
  const selfApprove = await supplier.request.post(`/api/v1/review/submissions/${id}/decision`, {
    headers: csrfHeaders(testInfo),
    data: { decision: "APPROVED", reason: "Approving my own business." },
  });
  expect(selfApprove.status()).toBe(403);

  await supplier.goto("/app/review");
  await expect(supplier.getByText("Only PaySetu reviewers can do this.")).toBeVisible();
  const menu = supplier.getByRole("button", { name: "Open menu" });
  if (await menu.isVisible()) await menu.click();
  await expect(supplier.getByRole("link", { name: "Cases" }).first()).toBeVisible();
  await expect(supplier.getByRole("link", { name: "Review queue" })).toHaveCount(0);
  await supplier.goto("/app/onboarding");
  await expect(supplier.getByText("Pending review").first()).toBeVisible();
  await supplier.context().close();
});

test("a reviewer-only account sees only reviewer pages, in both themes", async ({ page }) => {
  await page.goto("/app");
  await expect(page).toHaveURL(/\/app\/review$/);
  await page.goto("/app/cases");
  await expect(page).toHaveURL(/\/app\/review$/);
  const menu = page.getByRole("button", { name: "Open menu" });
  if (await menu.isVisible()) await menu.click();
  await expect(page.getByRole("link", { name: "Review queue" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Cases" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Record delivery" })).toHaveCount(0);
  await expect(
    page.getByText("PaySetu reviewer", { exact: true }).filter({ visible: true }).first(),
  ).toBeVisible();

  // Dark mode: nothing on the queue or a detail page keeps a light-mode surface.
  await page.evaluate(() => localStorage.setItem("paysetu-theme", "dark"));
  const queue = await (await page.request.get("/api/v1/review/submissions?all=true")).json();
  const paths = ["/app/review"];
  if (queue.items.length > 0) paths.push(`/app/review/${queue.items[0].submission_id}`);
  for (const path of paths) {
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(
      "rgb(23, 23, 23)",
    );
    const light = await page.evaluate(
      () =>
        [...document.querySelectorAll("body *")].filter((el) => {
          if (el.closest("nextjs-portal")) return false;
          const style = getComputedStyle(el);
          const visible = (el as HTMLElement).offsetParent !== null || style.position === "fixed";
          return (
            visible &&
            (style.backgroundColor === "rgb(255, 255, 255)" || style.color === "rgb(38, 38, 38)")
          );
        }).length,
    );
    expect(light, path).toBe(0);
  }
  await page.evaluate(() => localStorage.removeItem("paysetu-theme"));
});
