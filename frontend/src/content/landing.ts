// UI copy for the landing page (DESIGN.md Sections 12.1 and 13). Keep all user-facing strings here.

export const landingCopy = {
  productName: "PaySetu",
  headline: "Every delivery deserves a clear payment trail.",
  subheading:
    "Track payment timelines, protect important documents, and prepare your records before payment disputes escalate.",
  openDemo: "Open demo workspace",
  seeHow: "See how it works",
  demoNote:
    "Evaluation build running locally. Opening the workspace asks you to sign in or create an account. Do not enter real business or personal data.",
  previewLabel: "Sample content",
  previewNote: "An illustration of a case workspace. Dates and names here are not real.",
  stepsHeading: "How PaySetu works",
  stepsIntro: "One case per delivery, from the first record to a pack you can hand to a reviewer.",
  steps: [
    {
      title: "Record a delivery",
      body: "Log the invoice, the buyer and the delivery date. The case starts with a reference and a first timeline entry.",
    },
    {
      title: "Understand the payment timeline",
      body: "See the dates the MSMED Act counts from, calculated by the backend rules engine, with a short reason for each date.",
    },
    {
      title: "Preserve and verify evidence",
      body: "Every uploaded file is stored unchanged with a SHA-256 fingerprint, so a later change can be detected.",
    },
    {
      title: "Track objections",
      body: "Record each buyer reply, note when a written objection is removed, and watch how the dates respond.",
    },
    {
      title: "Prepare an evidence pack",
      body: "Download a ZIP with the case summary, timeline, your original files and a hash manifest, after an integrity check.",
    },
  ],
  notHeading: "What PaySetu is not",
  notBody:
    "PaySetu is not a law firm, collection agency, lawyer marketplace or government portal. It prepares and organises evidence; the ODR portal, Facilitation Councils and courts decide disputes.",
  disclaimer: "PaySetu prepares evidence. It is not legal advice.",
} as const;
