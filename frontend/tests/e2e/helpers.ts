import { expect, type Page } from "@playwright/test";

/** `YYYY-MM-DD` for `days` ago, in India time (the date the backend treats as "today"). */
export function isoDaysAgo(days: number): string {
  const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  now.setDate(now.getDate() - days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
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
