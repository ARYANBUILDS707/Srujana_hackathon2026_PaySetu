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
      title: "Export a claim pack",
      body: "Download an organised evidence pack for the MSME ODR portal or an advocate you choose.",
    },
  ],
  notHeading: "What PaySetu is not",
  notBody:
    "PaySetu is not a law firm, collection agency, lawyer marketplace or government portal. It prepares and organises evidence; the ODR portal, Facilitation Councils and courts decide disputes.",
  signUp: "Sign up",
  logIn: "Log in",
  accountsUnavailable: "Accounts are not available yet. Sign-up opens in a later release.",
  disclaimer: "PaySetu prepares evidence. It is not legal advice.",
} as const;
