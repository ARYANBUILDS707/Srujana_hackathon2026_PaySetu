import type { components } from "./schema";

// Response and request shapes come straight from the backend OpenAPI schema (`make api-types`).
type S = components["schemas"];

export type Supplier = S["SupplierOut"];
export type Buyer = S["BuyerOut"];
export type BuyerCreate = S["BuyerCreate"];
export type CaseSummary = S["CaseSummaryOut"];
export type CaseDetail = S["CaseOut"];
export type CaseCreate = S["CaseCreate"];
export type Clock = S["ClockOut"];
export type Checklist = S["ChecklistOut"];
export type ChecklistItem = S["ChecklistItemOut"];
export type Interest = S["InterestOut"];
export type BuyerResponse = S["ResponseOut"];
export type ResponseCreate = S["ResponseCreate"];
export type Evidence = S["EvidenceOut"];
export type TimelineEvent = S["TimelineEventOut"];
export type Integrity = S["IntegrityOut"];
export type EvidenceKind = S["EvidenceKind"];
export type ResponseKind = S["ResponseKind"];
export type ResponseChannel = S["ResponseChannel"];
export type DealType = S["DealType"];
export type Me = S["MeOut"];
export type SignupBody = S["SignupIn"];
export type LoginBody = S["LoginIn"];
export type PasswordUpdated = S["PasswordUpdatedOut"];
export type ForgotPasswordResult = S["ForgotPasswordOut"];
