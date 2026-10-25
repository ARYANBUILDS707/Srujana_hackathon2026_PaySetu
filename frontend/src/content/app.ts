// UI copy for the application screens (DESIGN.md Section 13: plain language, honest labels).
// Legal wording follows the PRD: PaySetu "reads the Act as...", never "you will win".

import type { CaseDetail, EvidenceKind, ResponseChannel, ResponseKind } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

export const appCopy = {
  productName: "PaySetu",
  // Dashboard only: a single short disclaimer.
  shortDisclaimer: "PaySetu prepares evidence. It is not legal advice.",
  nav: [
    { href: "/app", label: "Dashboard", match: "exact", icon: "dashboard" as const },
    { href: "/app/cases", label: "Cases", match: "prefix", icon: "cases" as const },
    {
      href: "/app/onboarding",
      label: "Business profile",
      match: "exact",
      icon: "building" as const,
    },
    { href: "/app/settings", label: "Settings", match: "exact", icon: "settings" as const },
  ],
  primaryAction: { href: "/app/cases/new", label: "Record delivery" },
  caseTabs: [
    { slug: "", label: "Overview" },
    { slug: "evidence", label: "Evidence" },
    { slug: "responses", label: "Buyer responses" },
    { slug: "checklist", label: "Case Strength" },
    { slug: "interest", label: "Interest" },
    { slug: "timeline", label: "Timeline" },
  ],
  shaExplainer:
    "SHA-256 checks whether stored file contents match their recorded fingerprints. It does not independently establish document authenticity.",
  evidencePack: {
    description: "A ZIP of the case file with a SHA-256 manifest, built from the stored evidence.",
    contents: [
      "Case summary, DeemedClock dates, interest and the rules relied on",
      "Timeline (readable and as JSON) and the Case Strength checklist",
      "A verification report",
      "Your original evidence files, unchanged",
      "manifest.json: a SHA-256 hash for every file",
    ],
    notice:
      "This export is prepared for review and is not a court-certified document or an official filing. It holds synthetic demo data, and no Section 63 certificate is included. The export is refused if any file or the timeline fails verification.",
  },
  pendingReview: {
    title: "Pending legal review",
    body: "Some rules behind these dates and amounts are interpretations that an advocate has not confirmed yet. Treat every figure as illustrative.",
  },
  unverifiedRate:
    "The bank rate used here has not been verified against an RBI notification. This figure is illustrative only.",
};

/** Plain-language meanings for the DeemedClock (PaySetu's reading; pending legal review). */
export const clockGlossary = [
  {
    term: "Objection window",
    meaning:
      "The 15 days after delivery (the delivery day itself is not counted) in which the buyer can object in writing. Email, letters and chat messages count as writing; a phone call does not.",
  },
  {
    term: "Acceptance",
    meaning:
      'If the buyer makes no written objection within those 15 days, the delivery day itself counts as the day of acceptance ("deemed acceptance"). If the buyer objects in writing in time, acceptance is the day the objection is removed.',
  },
  {
    term: "Payment deadline",
    meaning:
      "Without a written agreement, payment is due within 15 days of acceptance. With a written agreement, by the agreed date, and never more than 45 days after acceptance.",
  },
  {
    term: "Interest start",
    meaning:
      "If payment is late, interest can run from the day after the deadline. PaySetu shows it as an illustrative figure only.",
  },
];

export const acceptanceStateLabel: Record<string, string> = {
  window_open: "Objection window open",
  objection_raised: "Objection raised",
  accepted: "Accepted",
};

export const paymentStateLabel: Record<string, string> = {
  not_due: "Not due yet",
  overdue: "Overdue",
  settled: "Settled",
};

export const evidenceKindLabel: Record<EvidenceKind, string> = {
  invoice: "Invoice",
  delivery_challan: "Delivery challan",
  delivery_photo: "Delivery photo",
  purchase_order: "Purchase order",
  written_terms: "Written payment terms",
  email: "Email (.eml)",
  chat_export: "Chat export",
  tracking_record: "Tracking record",
  udyam_certificate: "Udyam certificate",
  buyer_response: "Buyer response",
  payment_proof: "Payment proof",
  communication_proof: "Communication proof",
  other: "Other",
};

/** One line under the evidence type picker: what that kind of file is for. */
export const evidenceKindGuidance: Partial<Record<EvidenceKind, string>> = {
  invoice: "The invoice issued to the buyer. It is a required item.",
  delivery_challan: "A signed or stamped challan is proof of delivery.",
  delivery_photo: "A photo of the goods or of the buyer's receipt.",
  purchase_order: "The buyer's order, if there was one.",
  written_terms: "Any document that shows the agreed payment period.",
  email: "Save the message as an .eml file so its headers are kept.",
  chat_export: "Export the chat as text. Screenshots are weaker than the export.",
  tracking_record: "Courier or transporter tracking showing delivery.",
  buyer_response: "A reply from the buyer, such as a written objection.",
  payment_proof: "A bank entry or receipt for any part-payment.",
  other: "Anything else that helps explain the delivery.",
};

export const uploadKinds: EvidenceKind[] = [
  "invoice",
  "delivery_challan",
  "delivery_photo",
  "purchase_order",
  "written_terms",
  "email",
  "chat_export",
  "tracking_record",
  "buyer_response",
  "payment_proof",
  "other",
];

export const responseKindLabel: Record<ResponseKind, string> = {
  objection: "Objection",
  acknowledgement: "Acknowledgement",
  other: "Other reply",
};

export const responseChannelLabel: Record<ResponseChannel, string> = {
  email: "Email",
  letter: "Letter",
  whatsapp: "WhatsApp or chat message",
  in_person_written: "Written note handed over",
  phone_note: "Phone call (not in writing)",
  other: "Other",
};

export const checklistStatusLabel: Record<string, string> = {
  met: "Met",
  missing: "Missing",
  warning: "Needs attention",
  not_applicable: "Not applicable",
};

export const eligibilityLabel: Record<string, string> = {
  eligible: "Eligible",
  eligible_with_warnings: "Eligible, with warnings",
  not_eligible: "Not eligible",
  cannot_assess: "Cannot assess",
};

export const eventTypeLabel: Record<string, string> = {
  case_created: "Delivery recorded",
  evidence_added: "Evidence added",
  response_recorded: "Buyer response recorded",
  objection_removed: "Objection marked as removed",
  integrity_verified: "Integrity check passed",
  integrity_failed: "Integrity check failed",
};

interface NextActionCopy {
  title: string;
  body: string;
  href: string;
  cta: string;
}

/** DESIGN.md Section 9.4. Letters and packs are not in this build, so copy says so. */
export function nextActionCopy(next: CaseDetail["next_action"], caseId: string): NextActionCopy {
  const base = `/app/cases/${caseId}`;
  switch (next.code) {
    case "review_integrity":
      return {
        title: "Review the integrity problem",
        body: "A stored file or timeline entry no longer matches its recorded hash.",
        href: `${base}/evidence`,
        cta: "Open Evidence",
      };
    case "resolve_objection":
      return {
        title: "Resolve the objection and record when it was removed",
        body: "Acceptance is not fixed while a written objection from the window is open.",
        href: `${base}/responses`,
        cta: "Open Buyer responses",
      };
    case "send_intimation":
      return {
        title: "Tell the buyer about this delivery",
        body: "Letter drafting is not part of this demo build. Send the intimation yourself, then keep proof of it as evidence.",
        href: `${base}/evidence`,
        cta: "Add evidence",
      };
    case "complete_evidence":
      return completeEvidenceCopy(next.checklist_item, base);
    case "send_demand":
      return {
        title: "Send a demand to the buyer",
        body: "Payment is overdue. Demand letters are not part of this demo build; send one yourself and keep proof of it.",
        href: `${base}/evidence`,
        cta: "Add evidence",
      };
    case "generate_pack":
      return {
        title: "Download the evidence pack",
        body: "The required evidence is in place. Download the pack: PaySetu checks every file and the timeline before building it.",
        href: `${base}#evidence-pack`,
        cta: "Go to Evidence pack",
      };
    case "share_or_file":
      return {
        title: "Share with your advocate or file on the ODR portal",
        body: "Filing is done by you on the official portal; PaySetu does not file for you.",
        href: `${base}/checklist`,
        cta: "Review Case Strength",
      };
    case "close_case":
      return {
        title: "Close this case",
        body: "The outstanding principal is zero.",
        href: `${base}/timeline`,
        cta: "View timeline",
      };
    default:
      return {
        title: "Nothing to do now",
        body: next.until
          ? `The next date that matters is ${formatDate(next.until)}.`
          : "We will show the next step when something changes.",
        href: `${base}/timeline`,
        cta: "View timeline",
      };
  }
}

/** What fixes each checklist gap that can be the next step (DESIGN.md 9.4, rule 4). */
function completeEvidenceCopy(item: string | null | undefined, base: string): NextActionCopy {
  switch (item) {
    case "C06":
      return {
        title: "Upload the invoice",
        body: "The invoice file is required and is not in this case yet.",
        href: `${base}/evidence`,
        cta: "Add evidence",
      };
    case "C07":
      return {
        title: "Complete the buyer and invoice details",
        body: "Invoice details are incomplete, for example the buyer's GSTIN. Add a buyer with those details when logging a delivery; the Case Strength tab shows what is missing.",
        href: `${base}/checklist`,
        cta: "See what is missing",
      };
    case "C08":
      return {
        title: "Upload proof of delivery",
        body: "Add the signed challan, a delivery photo or a tracking record.",
        href: `${base}/evidence`,
        cta: "Add evidence",
      };
    case "C10":
      return {
        title: "Upload the written payment terms",
        body: "The deal is recorded as having written terms, but no document showing them is in the case.",
        href: `${base}/evidence`,
        cta: "Add evidence",
      };
    default:
      return {
        title: "Add the missing evidence",
        body: "A required item is still missing.",
        href: `${base}/checklist`,
        cta: "See what is missing",
      };
  }
}

/** The one-sentence state under the DayStrip (DESIGN.md 5.6). */
export function windowSentence(clock: CaseDetail["clock"]): string {
  const acceptance = clock.acceptance_date ? formatDate(clock.acceptance_date) : null;
  switch (clock.acceptance_state) {
    case "window_open":
      return `Day ${clock.window_day} of 15 · ${clock.window_days_remaining} ${
        clock.window_days_remaining === 1 ? "day" : "days"
      } left for the buyer to object in writing.`;
    case "objection_raised":
      return "A written objection was received within the window. The acceptance date is fixed only when it is removed.";
    default:
      if (clock.acceptance_basis === "objection_removed")
        return `Accepted on ${acceptance}: the day the last written objection was removed.`;
      if (clock.acceptance_basis === "acknowledged")
        return `Accepted on ${acceptance}: the buyer acknowledged delivery and made no written objection by Day 15.`;
      return `Deemed accepted on ${acceptance} (no written objection by Day 15).`;
  }
}
