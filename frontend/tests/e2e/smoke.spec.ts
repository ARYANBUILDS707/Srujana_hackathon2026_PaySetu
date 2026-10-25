import { expect, test } from "@playwright/test";
import { signUpWithSampleBuyer } from "./helpers";

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

test("landing page opens the workspace for a signed-in supplier", async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/");
  await page.getByRole("link", { name: "Open demo workspace" }).click();

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("Demo mode.")).toHaveCount(0); // the banner was removed
});

test("keyboard focus is visible on interactive elements", async ({ page }, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  // The workspace replaces a loading placeholder after the session check, which resets the
  // browser's focus starting point (in dev, onto the Next.js overlay). Start from the page:
  // a click on the top-left padding, which is not a control, then Tab through the controls.
  await page.mouse.click(1, 1);

  // Tab through every control until focus leaves the page (an empty dashboard on a phone has
  // only a few); each one must show a visible 2px outline.
  let checked = 0;
  for (let step = 0; step < 8; step++) {
    await page.keyboard.press("Tab");
    const outline = await page.evaluate(() => {
      const active = document.activeElement;
      if (!active || active === document.body) return null;
      const style = getComputedStyle(active);
      return { style: style.outlineStyle, width: parseFloat(style.outlineWidth) };
    });
    if (outline === null) break;
    expect(outline.style).not.toBe("none");
    expect(outline.width).toBeGreaterThanOrEqual(2);
    checked += 1;
  }
  expect(checked).toBeGreaterThanOrEqual(3);
});
