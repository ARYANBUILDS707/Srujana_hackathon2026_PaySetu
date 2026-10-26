// UI copy for business onboarding (Phase 7B) and its review outcomes (Phase 7C). Self-declared
// data; an approval is a reviewer's manual decision, never a government verification.

import type { OnboardingStatus, ReviewOutcome } from "@/lib/api/types";

export const onboardingCopy = {
  title: "Business profile",
  description:
    "Tell us about your enterprise and upload its Udyam certificate. Your details are submitted for review; nothing is verified automatically.",
  selfDeclared:
    "Everything here is self-declared. PaySetu has not checked it against the Udyam portal. The SHA-256 fingerprint records exactly which file you uploaded; it does not show that the certificate is genuine.",
  sections: {
    enterprise: "Enterprise",
    address: "Registered address",
    contact: "Business contact",
    representative: "Representative and authority",
    certificate: "Udyam certificate",
  },
  labels: {
    enterprise_name: "Registered enterprise name",
    udyam_number: "Udyam Registration Number",
    enterprise_class: "Enterprise classification",
    registration_date: "Udyam registration date",
    address_line1: "Address line 1",
    address_line2: "Address line 2",
    city: "City or town",
    state: "State",
    pin_code: "PIN code",
    contact_email: "Business contact email",
    contact_phone: "Business contact phone",
    representative_name: "Representative name",
    representative_role: "Representative role",
    authorisation_note: "Authorisation details",
    authority_confirmed:
      "I am authorised to act for this enterprise, and these details match its Udyam registration to the best of my knowledge.",
    certificate: "Udyam certificate (PDF)",
  } as Record<string, string>,
  hints: {
    udyam_number: "Format UDYAM-XX-00-0000000, as printed on the certificate.",
    enterprise_class: "As stated on your Udyam certificate. Self-declared until reviewed.",
    registration_date: "Optional. The date on the certificate.",
    contact_phone: "Optional. 10-digit Indian mobile number.",
    authorisation_note:
      "Optional. For example: partner since 2019, or a board resolution naming you. Do not enter Aadhaar, PAN or bank details.",
    certificate: "PDF only, up to 5 MB. Download it from the Udyam portal and upload it unchanged.",
  } as Record<string, string>,
  classes: [
    { value: "micro", label: "Micro" },
    { value: "small", label: "Small" },
    { value: "medium", label: "Medium" },
  ],
  roles: [
    { value: "proprietor", label: "Proprietor" },
    { value: "partner", label: "Partner" },
    { value: "designated_partner", label: "Designated partner (LLP)" },
    { value: "director", label: "Director" },
    { value: "authorised_signatory", label: "Authorised signatory" },
    { value: "other", label: "Other" },
  ],
  udyamPreview: (value: string) => `Will be saved as ${value}`,
  udyamFormat: "Use the format UDYAM-XX-00-0000000 (two letters, two digits, seven digits).",
  claimConflict:
    "Another PaySetu account has already submitted this Udyam number. You can still submit: both claims will be reviewed. A matching number alone does not prove ownership.",
  save: "Save draft",
  saved: "Draft saved.",
  review: "Review & submit",
  upload: "Upload certificate",
  replace: "Replace certificate",
  uploading: (percent: number) => `Uploading ${percent}%`,
  uploaded: "Certificate uploaded.",
  current: "Current certificate",
  download: "Download",
  reviewTitle: "Review your details",
  reviewIntro:
    "Check everything below. After you submit, the details are locked for review and cannot be edited.",
  missingTitle: "Complete these before submitting",
  submit: "Submit for review",
  back: "Back to edit",
  submittedTitle: "Submitted for review",
  submittedBody:
    "Your business details and certificate have been submitted. They are locked while the review is pending.",
  reviewPending:
    "A PaySetu reviewer checks these details by hand. The status never changes to Approved automatically, and an approval is a reviewer's decision, not a government verification.",
  outcome: {
    APPROVED: {
      title: "Approved by a PaySetu reviewer",
      body: "A reviewer checked your submitted details by hand and approved them. This is PaySetu's review decision, not a government verification. Your cases and their legal calculations are unaffected.",
    },
    REJECTED: {
      title: "Not approved",
      body: "A reviewer could not approve these details. The submission is closed; contact PaySetu support if you think this is wrong.",
    },
    NEEDS_INFORMATION: {
      title: "The reviewer needs more information",
      body: "Correct your details below and submit again. Your earlier submission is kept unchanged in the history.",
    },
  } satisfies Record<ReviewOutcome["decision"], { title: string; body: string }>,
  reasonLabel: "Reviewer's reason",
  decidedOn: (when: string) => `Decided ${when}`,
  awaitingReview: "Awaiting review",
  history: "Submission history",
  revision: (n: number) => `Submission ${n}`,
  contested: "Number also claimed by another account",
  fingerprint: "Snapshot fingerprint (SHA-256)",
  settingsLabel: "Business verification",
  settingsLink: "Open business profile",
} as const;

export const onboardingStatusLabel: Record<OnboardingStatus, string> = {
  NOT_STARTED: "Not started",
  DRAFT: "Draft",
  PENDING_REVIEW: "Pending review",
  NEEDS_INFORMATION: "Needs information",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

export const onboardingStatusTone = {
  NOT_STARTED: "neutral",
  DRAFT: "neutral",
  PENDING_REVIEW: "primary",
  NEEDS_INFORMATION: "warning",
  APPROVED: "success",
  REJECTED: "danger",
} as const;
