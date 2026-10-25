// UI copy for the landing page (DESIGN.md Sections 12.1 and 13). Keep all user-facing strings here.
// No testimonials, user counts or recovery figures: the product has none to report.

export const landingCopy = {
  productName: "PaySetu",
  eyebrow: "For Indian micro and small suppliers",
  headlineLead: "Every payment has a",
  headlineAccent: "deadline.",
  headlineTail: "Every business deserves clarity.",
  subheading:
    "PaySetu keeps each delivery's documents, buyer replies and payment dates in one place, so you know where you stand before a delay becomes a dispute.",
  openDemo: "Open demo workspace",
  seeHow: "See how it works",
  signIn: "Sign in",
  createAccount: "Create account",
  demoNote:
    "Evaluation build running locally. Opening the workspace asks you to sign in or create an account. Do not enter real business or personal data.",
  previewLabel: "Sample content",
  previewNote: "An illustration of a case. Names, dates and amounts are not real.",
  stepsHeading: "How PaySetu works",
  stepsIntro: "One case per delivery, from the first record to a pack you can hand to a reviewer.",
  steps: [
    {
      title: "Record a delivery",
      body: "Log the invoice, the buyer and the delivery date. The case gets a reference and a first timeline entry.",
    },
    {
      title: "See the payment timeline",
      body: "The dates the MSMED Act counts from, worked out by PaySetu's rules engine, each with a short reason.",
    },
    {
      title: "Keep the evidence",
      body: "Each file is stored unchanged with a SHA-256 fingerprint, so a later change can be detected.",
    },
    {
      title: "Track buyer replies",
      body: "Record objections and when they were withdrawn, and watch how the dates respond.",
    },
    {
      title: "Prepare an evidence pack",
      body: "Download a ZIP with the summary, timeline, original files and a hash manifest, after an integrity check.",
    },
  ],
  featuresHeading: "Five tools, one case file",
  featuresIntro: "Each part answers one question a supplier asks when a buyer pays late.",
  features: {
    clock: {
      title: "DeemedClock",
      question: "When does payment fall due?",
      body: "Delivery, the 15-day window for written objections, acceptance, the payment deadline and when interest starts, in plain language.",
    },
    vault: {
      title: "Evidence Vault",
      question: "Is my proof safe?",
      body: "Invoices, challans and messages stored unchanged. A fingerprint shows whether a file changed; it does not prove a document is genuine.",
    },
    strength: {
      title: "Case Strength",
      question: "What is still missing?",
      body: "A checklist of what is in your file and what to add next. It measures readiness, not your chances.",
    },
    interest: {
      title: "Interest",
      question: "What could the buyer owe?",
      body: "An illustrative figure from the recorded bank rate, with every assumption shown.",
    },
    pack: {
      title: "Evidence Pack",
      question: "What do I hand over?",
      body: "One ZIP, built only after every file and the timeline pass verification.",
    },
  },
  notHeading: "What PaySetu is not",
  notBody:
    "PaySetu is not a law firm, collection agency, lawyer marketplace or government portal. It prepares and organises evidence; the ODR portal, Facilitation Councils and courts decide disputes.",
  honestHeading: "Honest by design",
  honest: [
    "Dates and amounts are illustrative until the legal rules are reviewed by an advocate.",
    "Business details you submit are self-declared; PaySetu does not verify them automatically.",
    "A SHA-256 fingerprint shows a file has not changed since upload. It is not proof that the document is authentic.",
  ],
  disclaimer: "PaySetu prepares evidence. It is not legal advice.",
} as const;
