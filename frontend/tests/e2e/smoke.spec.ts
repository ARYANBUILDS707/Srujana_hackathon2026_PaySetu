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

test("landing page opens the demo workspace", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Open demo workspace" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Demo mode.")).toBeVisible();
});

test("keyboard focus is visible on interactive elements", async ({ page }) => {
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

  for (let step = 0; step < 4; step++) {
    await page.keyboard.press("Tab");
    const outline = await page.evaluate(() => {
      const style = getComputedStyle(document.activeElement as Element);
      return { style: style.outlineStyle, width: parseFloat(style.outlineWidth) };
    });
    expect(outline.style).not.toBe("none");
    expect(outline.width).toBeGreaterThanOrEqual(2);
  }
});
