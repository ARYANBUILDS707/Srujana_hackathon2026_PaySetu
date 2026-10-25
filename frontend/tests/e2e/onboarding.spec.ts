// Phase 7B in the browser: business onboarding draft, certificate upload, review and
// submission, locking after submission, cross-user isolation and duplicate Udyam claims.

import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { csrfHeaders, signUpWithSampleBuyer } from "./helpers";

function pdf(label: string): Buffer {
  return Buffer.from(
    `%PDF-1.4\n% SAMPLE e2e certificate ${label}, not a real document\n` +
      "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
      "2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n" +
      "xref\n0 3\ntrailer<</Root 1 0 R/Size 3>>\nstartxref\n9\n%%EOF\n",
  );
}

/** A unique, well-formed (not real) Udyam number for this test run. */
function udyamFor(testInfo: TestInfo): string {
  const digits = String(Date.now() % 10_000_000).padStart(7, "0");
  return `UDYAM-${testInfo.project.name.startsWith("mobile") ? "MH" : "KA"}-12-${digits}`;
}

async function fillDraft(page: Page, udyam: string) {
  await page.getByLabel("Registered enterprise name").fill("E2E Fasteners (TEST)");
  await page.getByLabel("Udyam Registration Number").fill(udyam);
  await page.getByLabel("Enterprise classification").selectOption("micro");
  await page.getByLabel("Address line 1").fill("Plot 7, Sample Industrial Estate");
  await page.getByLabel("City or town").fill("Pune");
  await page.getByLabel("State").fill("Maharashtra");
  await page.getByLabel("PIN code").fill("411001");
  await page.getByLabel("Business contact email").fill("accounts@sample.example");
  await page.getByLabel("Representative name").fill("Sample Proprietor");
  await page.getByLabel("Representative role").selectOption("proprietor");
  await page.getByRole("checkbox").check();
}

async function uploadCertificate(page: Page, name: string, buffer: Buffer) {
  await page.getByLabel("Udyam certificate (PDF)").setInputFiles({
    name,
    mimeType: "application/pdf",
    buffer,
  });
  await page.getByRole("button", { name: /Upload certificate|Replace certificate/ }).click();
}

test("a supplier saves a draft, uploads the certificate and submits for review", async ({
  page,
}, testInfo) => {
  await signUpWithSampleBuyer(page, testInfo);
  await page.goto("/app/onboarding");
  await expect(page.getByRole("heading", { name: "Business profile" })).toBeVisible();
  await expect(page.getByText("Not started")).toBeVisible();

  // Invalid Udyam number: guidance in the browser, refusal from the server.
  await page.getByLabel("Udyam Registration Number").fill("UDYAM-MH-12-123");
  await expect(page.getByText("Use the format UDYAM-XX-00-0000000")).toBeVisible();
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(
    page.getByText(/Enter the Udyam Registration Number as UDYAM-XX-00-0000000/),
  ).toBeVisible();

  const udyam = udyamFor(testInfo);
  await fillDraft(page, udyam.toLowerCase().replaceAll("-", " "));
  await expect(page.getByText(`Will be saved as ${udyam}`)).toBeVisible();

  // A file that is not a PDF is refused.
  await uploadCertificate(page, "photo.pdf", Buffer.from("\x89PNG\r\n\x1a\n not a pdf"));
  await expect(page.getByText("Upload the certificate as a PDF file.")).toBeVisible();
  await uploadCertificate(page, "udyam-certificate.pdf", pdf(testInfo.project.name));
  await expect(page.getByText("Certificate uploaded.")).toBeVisible();
  await expect(page.getByTestId("current-certificate")).toContainText("udyam-certificate.pdf");

  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByText("Draft saved.")).toBeVisible();

  // Resume later: everything is still there.
  await page.reload();
  await expect(page.getByLabel("Udyam Registration Number")).toHaveValue(udyam);
  await expect(page.getByLabel("Registered enterprise name")).toHaveValue("E2E Fasteners (TEST)");
  await expect(page.getByText("Draft", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Review & submit" }).click();
  await expect(page.getByTestId("onboarding-review")).toContainText(udyam);
  await expect(page.getByTestId("onboarding-review")).toContainText("Micro (self-declared)");
  await page.getByRole("button", { name: "Submit for review" }).click();
  await expect(page.getByTestId("onboarding-submitted")).toContainText("Submitted for review");
  await expect(page.getByText("Pending review").first()).toBeVisible();
  await expect(page.getByText("never changes to Verified automatically")).toBeVisible();

  // Locked: the API refuses edits, and no route can verify.
  const edit = await page.request.put("/api/v1/onboarding/draft", {
    headers: csrfHeaders(testInfo),
    data: { enterprise_name: "Changed after submission" },
  });
  expect(edit.status()).toBe(409);
  const selfVerify = await page.request.put("/api/v1/onboarding/draft", {
    headers: csrfHeaders(testInfo),
    data: { status: "VERIFIED" },
  });
  expect(selfVerify.status()).toBe(422);

  await page.goto("/app/settings");
  await expect(page.getByTestId("business-status")).toContainText("Pending review");

  // The case workspace does not depend on the business review.
  await page.goto("/app/cases");
  await expect(page.getByRole("heading", { name: "Cases" })).toBeVisible();
});

test("another supplier cannot read the certificate and sees a duplicate claim warning", async ({
  page,
  browser,
}, testInfo) => {
  const udyam = udyamFor(testInfo).replace("-12-", "-34-");
  const headers = csrfHeaders(testInfo);

  // Supplier A submits through the API.
  await signUpWithSampleBuyer(page, testInfo);
  const draft = await page.request.put("/api/v1/onboarding/draft", {
    headers,
    data: {
      enterprise_name: "E2E Holder (TEST)",
      udyam_number: udyam,
      enterprise_class: "small",
      address_line1: "1 Sample Road",
      city: "Bengaluru",
      state: "Karnataka",
      pin_code: "560001",
      contact_email: "holder@sample.example",
      representative_name: "Sample Director",
      representative_role: "director",
      authority_confirmed: true,
    },
  });
  expect(draft.status()).toBe(200);
  const upload = await page.request.post("/api/v1/onboarding/certificate", {
    headers,
    multipart: { file: { name: "a.pdf", mimeType: "application/pdf", buffer: pdf("holder") } },
  });
  expect(upload.status()).toBe(201);
  const certificateId = (await upload.json()).certificate.id;
  expect((await page.request.post("/api/v1/onboarding/submit", { headers })).status()).toBe(200);

  // Supplier B, in a separate browser context.
  const otherContext = await browser.newContext({ baseURL: String(testInfo.project.use.baseURL) });
  const other = await otherContext.newPage();
  await signUpWithSampleBuyer(other, testInfo);
  const stolen = await other.request.get(
    `/api/v1/onboarding/certificates/${certificateId}/download`,
  );
  expect(stolen.status()).toBe(404);

  await other.goto("/app/onboarding");
  await expect(other.getByText("Not started")).toBeVisible();
  await fillDraft(other, udyam);
  await other.getByRole("button", { name: "Save draft" }).click();
  await expect(
    other.getByText("Another PaySetu account has already submitted this Udyam number"),
  ).toBeVisible();
  await otherContext.close();
});
