// A full supplier journey against the real backend (see playwright.config.ts).
// Delivery is 20 days ago (India time), so the 15-day window has closed and payment is overdue.

import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";
import { isoDaysAgo, logDelivery, signUpWithSampleBuyer } from "./helpers";

// Every test works as its own freshly signed-up supplier (Phase 6).
test.beforeEach(async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
});

test("supplier logs a delivery, adds evidence, verifies integrity and reviews the case", async ({
  page,
}, testInfo) => {
  const invoice = `E2E-${testInfo.project.name}-${Date.now()}`;
  await logDelivery(page, invoice);

  // DeemedClock: the engine's result, shown as returned by the API.
  await expect(page.getByRole("heading", { name: /PS-\d{4}-\d{4}/ })).toBeVisible();
  await expect(page.getByTestId("window-sentence")).toContainText("Deemed accepted on");
  await expect(page.getByText("Overdue").first()).toBeVisible();
  await expect(page.getByText("Pending legal review").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Upload the invoice" })).toBeVisible();

  // Evidence Vault: upload and check the displayed SHA-256 against our own hash.
  await page.getByRole("link", { name: "Evidence", exact: true }).first().click();
  const content = Buffer.from("%PDF-1.4\n% SAMPLE e2e invoice, not real evidence\n");
  await page.getByLabel("File (required)").setInputFiles({
    name: "invoice-sample.pdf",
    mimeType: "application/pdf",
    buffer: content,
  });
  await page.getByRole("button", { name: "Add evidence" }).click();
  await expect(page.getByText("Evidence added and sealed")).toBeVisible();
  const list = page.getByTestId("evidence-list");
  await expect(list).toContainText("invoice-sample.pdf");
  await list.getByRole("button", { name: /SHA-256 hash/ }).click();
  await expect(page.getByTestId("full-hash")).toHaveText(
    createHash("sha256").update(content).digest("hex"),
  );

  // Integrity check against the stored bytes and the hash-chained timeline.
  await page.getByRole("button", { name: "Verify integrity" }).click();
  await expect(page.getByTestId("integrity-result")).toContainText("Integrity check passed");

  // Case Strength: the invoice requirement is now met; others stay honestly missing.
  await page.getByRole("link", { name: "Case Strength" }).first().click();
  await expect(page.getByTestId("check-C06")).toContainText("Met");
  await expect(page.getByTestId("check-C08")).toContainText("Missing");
  await expect(page.getByTestId("check-C16")).toContainText("Met");

  // Interest: from the engine and the recorded (unverified) bank rate.
  await page.getByRole("link", { name: "Interest", exact: true }).first().click();
  await expect(page.getByText("Unverified bank rate").first()).toBeVisible();
  await expect(page.getByTestId("interest-accrued")).toContainText(/Rs [\d,]+\.\d{2}/);

  // Timeline: created, evidence added, integrity verified, with a hash on every entry.
  await page.getByRole("link", { name: "Timeline" }).first().click();
  const timeline = page.getByTestId("timeline-list");
  await expect(timeline).toContainText("Delivery recorded");
  await expect(timeline).toContainText("Evidence added");
  await expect(timeline).toContainText("Integrity check passed");
});

test("an objection stops the clock and removing it moves acceptance", async ({
  page,
}, testInfo) => {
  await logDelivery(page, `E2E-OBJ-${testInfo.project.name}-${Date.now()}`);
  await expect(page.getByTestId("window-sentence")).toContainText("Deemed accepted on");

  await page.getByRole("link", { name: "Buyer responses" }).first().click();
  await page.getByLabel("Date received (required)").fill(isoDaysAgo(18));
  await page.getByLabel("What the buyer said (required)").fill("Sample objection: thread defects");
  await page.getByRole("button", { name: "Save response" }).click();
  await expect(page.getByTestId("response-list")).toContainText("Affects acceptance");

  await page.getByRole("link", { name: "Overview" }).first().click();
  await expect(page.getByTestId("window-sentence")).toContainText("written objection");
  await expect(page.getByText("Objection raised").first()).toBeVisible();

  await page.getByRole("link", { name: "Buyer responses" }).first().click();
  await page.getByLabel("Date the objection was removed").fill(isoDaysAgo(10));
  await page.getByRole("button", { name: "Mark objection removed" }).click();
  await expect(page.getByTestId("response-list")).toContainText("Removed");

  await page.getByRole("link", { name: "Overview" }).first().click();
  await expect(page.getByTestId("window-sentence")).toContainText(
    "last written objection was removed",
  );
});

test("invalid input is rejected by the server and shown to the user", async ({ page }) => {
  await page.goto("/app/cases/new");
  await expect(page.getByLabel("Buyer (required)")).toContainText("SAMPLE");
  await page.getByLabel("Invoice number (required)").fill("BAD-1");
  await page.getByLabel("Invoice amount (Rs) (required)").fill("100.001");
  await page.getByRole("button", { name: "Save delivery" }).click();

  await expect(
    page
      .getByText("This delivery could not be saved")
      .or(page.getByText("Some fields need attention")),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/app\/cases\/new$/);
});
