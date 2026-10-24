import { expect, test } from "@playwright/test";

test("landing page loads with PaySetu content and no horizontal scroll", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("PaySetu");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What PaySetu is not" })).toBeVisible();
  await expect(page.getByText("It is not legal advice.")).toBeVisible();

  const hasHorizontalScroll = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalScroll).toBe(false);
});

test("account actions are disabled until authentication ships", async ({ page }) => {
  await page.goto("/");

  for (const name of ["Sign up", "Log in"]) {
    await expect(page.getByRole("link", { name })).toHaveAttribute("aria-disabled", "true");
  }
});
