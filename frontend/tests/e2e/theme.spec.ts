// Light / dark / system theme (DESIGN.md Section 2.3): switching, persistence, system
// preference, no flash before first paint, no hydration warnings, and no light-theme colours
// left behind in dark mode. Backend-connected pages are loaded for real.

import { expect, test, type Page } from "@playwright/test";
import { logDelivery, signUpWithSampleBuyer, uploadEvidence } from "./helpers";

const DARK_CANVAS = "rgb(23, 23, 23)"; // #171717
const LIGHT_CANVAS = "rgb(250, 250, 248)"; // #FAFAF8

const theme = (page: Page) =>
  page.evaluate(() => document.documentElement.getAttribute("data-theme"));
const bodyBackground = (page: Page) =>
  page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const toggle = (page: Page) => page.getByTestId("theme-toggle").filter({ visible: true });

test("the top-bar toggle switches light, dark and light again, and is remembered", async ({
  page,
}, testInfo) => {
  await page.emulateMedia({ colorScheme: "light" });
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  expect(await theme(page)).toBe("light");
  expect(await bodyBackground(page)).toBe(LIGHT_CANVAS);

  await expect(toggle(page)).toHaveAttribute("aria-label", "Switch to dark theme");
  await toggle(page).click();
  await expect.poll(() => theme(page)).toBe("dark");
  await expect.poll(() => bodyBackground(page)).toBe(DARK_CANVAS); // no reload needed
  await expect(toggle(page)).toHaveAttribute("aria-label", "Switch to light theme");

  await page.reload();
  expect(await theme(page)).toBe("dark"); // persisted on this device
  await expect(toggle(page)).toHaveAttribute("aria-label", "Switch to light theme");

  await toggle(page).focus();
  await page.keyboard.press("Enter"); // keyboard operable
  await expect.poll(() => theme(page)).toBe("light");
  await page.reload();
  expect(await theme(page)).toBe("light");
});

test("settings offer light, dark and system, and system follows the device", async ({
  page,
}, testInfo) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app/settings");
  const group = page.getByRole("group", { name: "Colour theme" });
  await expect(group.getByRole("radio", { name: /System/ })).toBeChecked(); // default
  expect(await theme(page)).toBe("dark"); // device prefers dark

  await page.emulateMedia({ colorScheme: "light" });
  await expect.poll(() => theme(page)).toBe("light"); // follows the device live

  await group.getByRole("radio", { name: /Dark/ }).check();
  await expect.poll(() => theme(page)).toBe("dark");
  await page.reload();
  await expect(
    page.getByRole("group", { name: "Colour theme" }).getByRole("radio", { name: /Dark/ }),
  ).toBeChecked();
  expect(await theme(page)).toBe("dark"); // explicit choice beats the device

  await page
    .getByRole("group", { name: "Colour theme" })
    .getByRole("radio", { name: /Light/ })
    .check();
  await expect.poll(() => theme(page)).toBe("light");
});

test("a saved dark theme is applied before the page is drawn, without hydration warnings", async ({
  page,
}) => {
  const problems: string[] = [];
  page.on("console", (message) => {
    const text = message.text();
    if (/hydrat|did not match|server rendered/i.test(text)) problems.push(text);
  });
  await page.addInitScript(() => window.localStorage.setItem("paysetu-theme", "dark"));

  const response = await page.goto("/login", { waitUntil: "commit" });
  const html = (await response?.text()) ?? "";
  // The bootstrap script sits in <head>, before any page content.
  expect(html.indexOf("/theme-init.js")).toBeGreaterThan(-1);
  expect(html.indexOf("/theme-init.js")).toBeLessThan(html.indexOf("<body"));

  await page.waitForLoadState("domcontentloaded");
  expect(await theme(page)).toBe("dark"); // already dark when the DOM is first ready
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  for (const path of ["/", "/signup", "/forgot-password"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
  }
  expect(problems).toEqual([]);
});

test("every page renders in dark mode with no light-theme colours left behind", async ({
  page,
}, testInfo) => {
  test.setTimeout(120_000);
  await signUpWithSampleBuyer(page, testInfo);
  await logDelivery(page, `E2E-THEME-${testInfo.project.name}-${Date.now()}`);
  await uploadEvidence(page, {
    name: "invoice-sample.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from(`%PDF-1.4\n% SAMPLE theme ${Date.now()}, not real evidence\n`),
  });
  const caseUrl = page.url().replace(/\/evidence$/, "");
  await page.evaluate(() => window.localStorage.setItem("paysetu-theme", "dark"));

  const pages = [
    "/",
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
    "/app",
    "/app/cases",
    "/app/cases/new",
    caseUrl,
    `${caseUrl}/evidence`,
    `${caseUrl}/responses`,
    `${caseUrl}/checklist`,
    `${caseUrl}/interest`,
    `${caseUrl}/timeline`,
    "/app/onboarding",
    "/app/settings",
  ];
  const leftovers: string[] = [];
  for (const path of pages) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect(await theme(page), path).toBe("dark");
    expect(await bodyBackground(page), path).toBe(DARK_CANVAS);
    const found = await page.evaluate(() => {
      const bad: string[] = [];
      for (const element of Array.from(document.querySelectorAll("body *"))) {
        const style = getComputedStyle(element);
        if (style.display === "none" || style.visibility === "hidden") continue;
        if (element.closest("nextjs-portal")) continue; // the dev server's own overlay
        const isWhite = style.backgroundColor === "rgb(255, 255, 255)";
        const lightInk = style.color === "rgb(38, 38, 38)"; // light-theme ink #262626
        if (isWhite || lightInk) bad.push(`${element.tagName}.${element.className}`.slice(0, 80));
      }
      return bad;
    });
    if (found.length) leftovers.push(`${path}: ${found.slice(0, 3).join(" | ")}`);
  }
  expect(leftovers).toEqual([]);
});
