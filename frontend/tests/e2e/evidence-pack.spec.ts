import { createHash } from "node:crypto";
import { readdirSync, readFileSync, appendFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { logDelivery, uploadEvidence } from "./helpers";
import { readZip } from "./zip";

const sha256 = (data: Buffer) => createHash("sha256").update(data).digest("hex");

function storedCopy(content: Buffer): string {
  // The e2e backend's evidence store (see playwright.config.ts). Content is unique per test.
  const root = path.resolve(process.cwd(), "../backend/storage/e2e/evidence");
  const match = (readdirSync(root, { recursive: true }) as string[])
    .map((entry) => path.join(root, entry))
    .find((file) => {
      try {
        return readFileSync(file).equals(content);
      } catch {
        return false; // a directory
      }
    });
  if (!match) throw new Error("Stored evidence file not found");
  return match;
}

test("downloading the evidence pack in the browser gives a verifiable ZIP", async ({
  page,
}, testInfo) => {
  const content = Buffer.from(
    `%PDF-1.4\n% SAMPLE pack e2e ${testInfo.project.name} ${Date.now()}, not real evidence\n`,
  );
  await logDelivery(page, `E2E-PACK-${testInfo.project.name}-${Date.now()}`);
  await uploadEvidence(page, {
    name: "invoice-sample.pdf",
    mimeType: "application/pdf",
    buffer: content,
  });
  await page.getByRole("link", { name: "Overview" }).first().click();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download Evidence Pack" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^PaySetu-evidence-pack-PS-\d{4}-\d{4}\.zip$/);
  const zipPath = await download.path();
  const files = readZip(readFileSync(zipPath));

  // Expected documents and the original evidence, unchanged.
  for (const name of [
    "README_FIRST.md",
    "01_case_summary.md",
    "02_deemed_clock_and_interest.md",
    "03_timeline.md",
    "04_case_strength_checklist.md",
    "05_verification_report.md",
    "timeline.json",
    "manifest.json",
  ]) {
    expect(files.has(name), name).toBe(true);
  }
  const evidenceNames = [...files.keys()].filter((n) => n.startsWith("evidence/"));
  expect(evidenceNames).toHaveLength(1);
  expect(files.get(evidenceNames[0])?.equals(content)).toBe(true);

  // Manifest consistency, checked here independently of the backend.
  const manifestBytes = files.get("manifest.json") as Buffer;
  const manifest = JSON.parse(manifestBytes.toString("utf8")) as {
    files: { path: string; sha256: string; size_bytes: number }[];
    legally_certified: boolean;
    demo: boolean;
  };
  expect(manifest.demo).toBe(true);
  expect(manifest.legally_certified).toBe(false);
  expect(manifest.files.map((f) => f.path).sort()).toEqual(
    [...files.keys()].filter((n) => n !== "manifest.json").sort(),
  );
  for (const entry of manifest.files) {
    const data = files.get(entry.path) as Buffer;
    expect(sha256(data), entry.path).toBe(entry.sha256);
    expect(data.length, entry.path).toBe(entry.size_bytes);
  }
  expect((files.get("README_FIRST.md") as Buffer).toString("utf8")).toContain(
    "NOT LEGALLY CERTIFIED",
  );

  // The page shows the pack ID, and it is the hash of the manifest we just verified.
  await expect(page.getByTestId("pack-done")).toContainText("Evidence pack downloaded");
  await page
    .getByTestId("pack-done")
    .getByRole("button", { name: /Pack ID hash/ })
    .click();
  await expect(page.getByTestId("full-hash")).toHaveText(sha256(manifestBytes));
});

test("tampered evidence blocks the download and the page explains why", async ({
  page,
}, testInfo) => {
  const content = Buffer.from(
    `%PDF-1.4\n% SAMPLE tamper e2e ${testInfo.project.name} ${Date.now()}, not real evidence\n`,
  );
  await logDelivery(page, `E2E-TAMPER-${testInfo.project.name}-${Date.now()}`);
  await uploadEvidence(page, {
    name: "invoice-sample.pdf",
    mimeType: "application/pdf",
    buffer: content,
  });
  await page.getByRole("link", { name: "Overview" }).first().click();

  appendFileSync(storedCopy(content), " tampered");

  let downloaded = false;
  page.on("download", () => {
    downloaded = true;
  });
  await page.getByRole("button", { name: "Download Evidence Pack" }).click();

  const error = page.getByTestId("pack-error");
  await expect(error).toContainText("Pack not created");
  await expect(error).toContainText("no pack was created");
  await expect(error).toContainText("hash does not match the recorded hash");
  await expect(page.getByTestId("pack-done")).toHaveCount(0);
  expect(downloaded).toBe(false);
});
