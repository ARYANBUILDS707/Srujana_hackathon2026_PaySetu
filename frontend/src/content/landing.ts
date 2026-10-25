// UI copy for the landing page (DESIGN.md Sections 12.1 and 13). Keep all user-facing strings here.

export const landingCopy = {
  productName: "PaySetu",
  tagline: "Evidence-first delayed-payment protection for Indian micro and small enterprises.",
  intro:
    "PaySetu helps you record each delivery, track the 15-day window for buyer objections, keep tamper-evident proof, and prepare a claim pack if the buyer pays late.",
  stepsHeading: "What PaySetu does",
  steps: [
    {
      title: "Record the delivery",
      body: "Log the invoice and a photo of the signed challan, and see the dates the MSMED Act counts from.",
    },
    {
      title: "Keep sealed proof",
      body: "Every file gets a SHA-256 fingerprint and a time, so any later change can be detected.",
    },
    {
      title: "Check your case",
      body: "See what is missing from your file, and an illustrative interest figure from the recorded bank rates.",
    },
  ],
  notHeading: "What PaySetu is not",
  notBody:
    "PaySetu is not a law firm, collection agency, lawyer marketplace or government portal. It prepares and organises evidence; the ODR portal, Facilitation Councils and courts decide disputes.",
  openDemo: "Open the demo workspace",
  demoNote:
    "Evaluation build: synthetic supplier data, no login, running locally. Sign-up arrives in a later release.",
  disclaimer: "PaySetu prepares evidence. It is not legal advice.",
} as const;
