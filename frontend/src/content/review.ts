// UI copy for business review (Phase 7C). Reviewer decisions are manual checks by a person,
// never a government verification; SHA-256 shows integrity, not authenticity.

import type {
  CheckField,
  CheckResult,
  CheckSource,
  EvidenceLevel,
  ReviewSubmissionStatus,
} from "@/lib/api/types";

export const reviewCopy = {
  navLabel: "Review queue",
  queueTitle: "Review queue",
  queueDescription:
    "Business submissions waiting for a manual review. Oldest first. Decisions are final.",
  emptyTitle: "Nothing waiting",
  emptyBody: "No submissions match this filter.",
  loadMore: "Load more",
  ownBadge: "Your own business",
  duplicateBadge: (n: number) =>
    `Number also claimed by ${n} other ${n === 1 ? "account" : "accounts"}`,
  contestedBadge: "Contested at submission",
  checks: (n: number) =>
    n === 0 ? "No checks yet" : `${n} ${n === 1 ? "check" : "checks"} recorded`,
  open: "Open",
  back: "Back to queue",
  boundaryTitle: "What a review means",
  boundary:
    "A review records what a PaySetu reviewer checked by hand, where and when. PaySetu has no connection to the Udyam portal or any government system. An approval is a reviewer's decision, not a government verification.",
  submittedTitle: "Submitted by the supplier",
  submittedNotice:
    "Supplier-submitted and self-declared. Frozen at submission; it cannot be changed.",
  submittedBy: "Submitted by",
  snapshot: "Snapshot fingerprint (SHA-256)",
  snapshotIntact: "The stored snapshot matches its fingerprint.",
  snapshotBroken: "The stored snapshot no longer matches its fingerprint. Do not approve.",
  certificateTitle: "Udyam certificate",
  certificateIntact:
    "The stored file matches the SHA-256 recorded at upload. This shows the file is unchanged since upload, not that the certificate is genuine.",
  certificateBroken: "The stored file no longer matches its recorded SHA-256. Do not approve.",
  downloadCertificate: "Download certificate (PDF)",
  downloadHint: "Downloaded as an attachment. PaySetu never opens or renders it.",
  claimsTitle: "Other claims on this Udyam number",
  claimsNone: "No other supplier has submitted this number.",
  claimsIntro:
    "Other accounts have submitted the same Udyam number. A matching number alone does not prove ownership; approving one marks the other claims contested.",
  openClaim: "Open their submission",
  checksTitle: "Manual checks",
  checksNone: "No checks recorded yet. Approval needs at least one.",
  checksIntro: "Each check is permanent. To correct one, record a new check.",
  checkForm: "Record a manual check",
  sourceLabel: "Source consulted",
  sourceDetailLabel: "What exactly you consulted",
  sourceDetailHint:
    "For example: the Udyam portal page you used and the number you searched. Name the record, not just the website.",
  checkedOnLabel: "Date of the check",
  checkedOnHint: "The day you looked. Not in the future.",
  itemsLegend: "Compare the submitted details with what you saw",
  observedLabel: "What you saw at the source",
  resultLabel: "Result",
  notCompared: "Not compared",
  noteLabel: "Note for reviewers (optional)",
  recordCheck: "Record check",
  checkRecorded: "Check recorded.",
  decisionTitle: "Decision",
  decisionIntro: "Decisions are final and cannot be edited. The supplier sees the decision.",
  decisionLabel: "Decision",
  reasonLabel: "Reason",
  reasonHint:
    "At least 10 characters. Shown to the supplier for Needs information and Rejected; say exactly what to correct.",
  internalNoteLabel: "Internal note (optional)",
  internalNoteHint: "Only reviewers see this.",
  submitDecision: "Record decision",
  confirmDecision: (label: string) => `Record "${label}"? This cannot be undone.`,
  decided: "Decision recorded",
  ownNotice:
    "You own or submitted this business, so you cannot check or decide it. Another reviewer must.",
  noDecisionNeeded: "This submission has already been decided.",
  historyTitle: "Review history",
  revision: (n: number) => `Submission ${n}`,
  by: (name: string) => `by ${name}`,
  internalNote: "Internal note",
  evidenceTitle: "How the details are supported",
} as const;

export const submissionStatusLabel: Record<ReviewSubmissionStatus, string> = {
  PENDING_REVIEW: "Pending review",
  NEEDS_INFORMATION: "Needs information",
  APPROVED: "Approved",
  REJECTED: "Rejected",
};

export const submissionStatusTone = {
  PENDING_REVIEW: "primary",
  NEEDS_INFORMATION: "warning",
  APPROVED: "success",
  REJECTED: "danger",
} as const;

export const queueFilters: { value: ReviewSubmissionStatus | "all"; label: string }[] = [
  { value: "PENDING_REVIEW", label: "Pending" },
  { value: "NEEDS_INFORMATION", label: "Needs information" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "all", label: "All" },
];

export const decisionOptions: {
  value: "APPROVED" | "NEEDS_INFORMATION" | "REJECTED";
  label: string;
}[] = [
  { value: "NEEDS_INFORMATION", label: "Request more information" },
  { value: "REJECTED", label: "Reject" },
  { value: "APPROVED", label: "Approve" },
];

export const checkSourceLabel: Record<CheckSource, string> = {
  udyam_portal: "Udyam Registration portal (looked up manually)",
  other_official_record: "Another official record",
  certificate_only: "Uploaded certificate only",
  other: "Other source",
};

export const checkFieldLabel: Record<CheckField, string> = {
  udyam_number: "Udyam Registration Number",
  enterprise_name: "Enterprise name",
  enterprise_class: "Classification",
  registration_date: "Registration date",
  address: "Registered address",
  representative_name: "Representative name",
};

export const checkResultLabel: Record<CheckResult, string> = {
  match: "Matches",
  mismatch: "Does not match",
  not_found: "Not found at the source",
};

export const checkResultTone = {
  match: "success",
  mismatch: "danger",
  not_found: "warning",
} as const;

export const evidenceLevelCopy: Record<EvidenceLevel, { label: string; body: string }> = {
  supplier_submitted: {
    label: "Supplier-submitted only",
    body: "No reviewer has checked these details yet. Everything shown is what the supplier declared.",
  },
  manually_reviewed: {
    label: "Manually reviewed",
    body: "A reviewer has recorded a check, but not one where the Udyam number and enterprise name both matched an official record with no mismatch.",
  },
  official_record_matched: {
    label: "Matched an official record (manual check)",
    body: "A reviewer recorded that the Udyam number and enterprise name matched an official record they consulted by hand, with no mismatch. This is a person's record of a manual lookup, not a government verification.",
  },
};
