# PaySetu: API Specification

| Field | Value |
| --- | --- |
| Status | Draft v1.1 (consistency review), derived from PRD.md, ARCHITECTURE.md and DATABASE.md v1.1 |
| Base path | `/api/v1` (same origin as the web app) |
| Format | JSON (`application/json`), multipart for uploads, ZIP/PDF for downloads |
| Machine contract | FastAPI-generated OpenAPI at `/api/v1/openapi.json` (disabled in production unless `APP_ENV != production`). Frontend types are generated from it |

---

## 1. Conventions

### 1.1 General

- Resource names are plural and kebab-case where multi-word (`/share-links`). JSON fields are `snake_case`.
- IDs are UUID strings. Case references (`PS-2026-0042`) are for display only, never used as path IDs.
- **Money** is sent and returned as a decimal string in rupees with 2 decimals: `"500000.00"`. Never as a JSON number.
- **Legal dates** are `YYYY-MM-DD` (Asia/Kolkata calendar). **Timestamps** are ISO-8601 UTC with `Z`.
- **Rates** are decimal strings in percent: `"17.25"`.
- Computed blocks (`clock`, `interest`, `checklist`, `next_action`) are always computed server-side at request time. They include `as_of` and `rule_set_version`.
- Every response carries an `X-Request-ID` header.
- Unknown JSON fields in requests are rejected (`extra = forbid`).

### 1.2 Authentication

| Route group | Mechanism |
| --- | --- |
| `/auth/*` (signup, login) | None (rate-limited) |
| Supplier routes | `ps_session` cookie (HttpOnly, SameSite=Lax, Path=/; Secure whenever `PUBLIC_BASE_URL` is https, so always in production) |
| `/public/share/{token}/*` | Share token in the path; no cookie needed |
| `/health` | None |

**Unsafe methods** (POST, PUT, PATCH, DELETE) on cookie-authenticated routes also require:

- the `Origin` header to equal `PUBLIC_BASE_URL` (or the `Referer` to start with it)
- the header `X-PaySetu-Client: web`

Failing either returns **403 `csrf_rejected`**. This includes `POST /auth/signup`, `/auth/login` and `/auth/logout`.

**Implemented (Phase 6, 25 Oct 2026):** signup, login, logout and me (Section 2.2). The session token is 256 random bits; only its SHA-256 is stored. Sessions end after `SESSION_IDLE_HOURS` without use (default 168, sliding) or `SESSION_ABSOLUTE_DAYS` after login (default 30), or on logout. Any 401 caused by a bad, expired or revoked cookie also clears the cookie (`Set-Cookie: ps_session=; Max-Age=0`).

### 1.3 Authorisation

- Every supplier route resolves `supplier_id` from the session. A resource belonging to another supplier returns **404 `not_found`** (never 403), so its existence is not revealed. **Implemented** for every case, buyer, response, evidence, download, integrity, timeline, checklist, interest and evidence-pack route (`backend/tests/integration/test_authorisation.py` walks every documented operation).
- Routes requiring a completed profile (case creation, sending) return **409 `profile_incomplete`** with the missing fields listed.
- Share-token routes return only the purpose-specific projection (Section 4).

### 1.4 Error format (`application/problem+json`)

```json
{
  "type": "https://paysetu.app/problems/validation_failed",
  "title": "Some fields need attention",
  "status": 422,
  "code": "validation_failed",
  "detail": "Delivery date cannot be in the future.",
  "request_id": "01JC…",
  "errors": [
    { "field": "delivery_date", "code": "date_in_future", "message": "Delivery date cannot be in the future." }
  ]
}
```

| HTTP | `code` values | When |
| --- | --- | --- |
| 400 | `bad_request` | Malformed JSON or multipart |
| 401 | `unauthenticated`, `session_expired`, `invalid_credentials` | No, revoked or unknown session; expired session; wrong email or password at login |
| 403 | `csrf_rejected`, `forbidden` | CSRF failure; action not allowed for this principal |
| 404 | `not_found` | Missing or not owned |
| 409 | `conflict`, `invalid_state`, `profile_incomplete`, `duplicate_evidence`, `already_sent`, `integrity_failed` | State conflicts |
| 410 | `link_expired`, `link_revoked` | Share links (an invalid token also returns `link_revoked`) |
| 413 | `file_too_large`, `case_storage_full` | Upload limits |
| 415 | `unsupported_file_type` | Upload type rejected |
| 422 | `validation_failed` | Field validation, with `errors[]` |
| 429 | `rate_limited` | With a `Retry-After` header |
| 502 | `integration_failed` | SMTP or provider failure (the request's own data is saved) |
| 500 | `internal_error` | Unexpected; generic message + `request_id` |

Messages are safe to show to users. Internal details never appear in responses.

### 1.5 Pagination, filtering, sorting

- Cursor pagination on list endpoints: `?limit=20&cursor=<opaque>`. `limit` max is 100.
- Response envelope: `{ "items": [...], "next_cursor": "…" | null }`.
- Filters are explicit query params documented per endpoint. Unknown params return 422.
- Small, bounded lists (responses, payments, communications, packs, share links per case) are returned in full without pagination.

### 1.6 Idempotency and concurrency

- State transitions (`approve`, `send`, `revoke`, `close`) are guarded server-side by conditional updates. Repeating a completed transition returns **409 `invalid_state`** or `already_sent`; it never performs the action twice.
- `POST /cases` and `POST /evidence` accept an optional `Idempotency-Key` header (a UUID). Within 24 h, a repeat with the same key and the same user returns the original result. This protects against double taps on poor mobile networks. Keys are held in memory in MVP (single instance).

---

## 2. Endpoints

**Legend.** Auth: **S** = supplier session, **T** = share token, **–** = none. Priority as in PRD.

### 2.1 Health

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | – | Liveness + readiness: `{ "status": "ok", "db": "ok", "storage": "ok", "modes": { "email": "simulated", "verification": "off" } }` |

### 2.2 Auth

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| POST | `/auth/signup` | – | Create a user, the user's supplier and a session. **Built** | P0 |
| POST | `/auth/login` | – | Create a session (revokes any session the browser already had). **Built** | P0 |
| POST | `/auth/logout` | – (cookie if present) | Revoke the current session and clear the cookie; idempotent, always 204. **Built** | P0 |
| GET | `/auth/me` | S | Current user and supplier summary (`Cache-Control: no-store`). **Built**; profile completeness and adapter modes not yet included | P0 |
| POST | `/auth/password/change` | S | Change password; revokes other sessions. **Not built yet** | P0 |
| POST | `/auth/password/forgot` | – | Always 202; sends a reset email if the account exists | P1 |
| POST | `/auth/password/reset` | – | Token + new password | P1 |

`POST /auth/signup`:

As built (Phase 6). `business_name` is an addition: signup creates the supplier too (DECISIONS.md Section 8).

```json
// request
{ "email": "ravi@example.in", "password": "••••••••••", "full_name": "Ravi Kumar",
  "business_name": "Ravi Fasteners", "accept_terms_version": "evaluation-2026-10" }
// 201 response (sets the ps_session cookie; the token never appears in a body)
{ "user": { "id": "…", "email": "ravi@example.in", "full_name": "Ravi Kumar" },
  "supplier": { "id": "…", "legal_name": "Ravi Fasteners", "demo_mode": false } }
```

`POST /auth/login` takes `{ "email": "…", "password": "…" }` and returns the same body as signup. `GET /auth/me` returns it for the current session.

Validation:

- `email` is a valid address.
- `password` is 10–128 characters and not on the common-password list.
- `email` is stored lower-cased and trimmed; `full_name` 1–120 and `business_name` 1–200 characters.
- `accept_terms_version` must equal the current version (`evaluation-2026-10`: the evaluation notice on the signup page, not counsel-reviewed Terms; DECISIONS.md Section 8).
- Submitted values (including passwords) never appear in error responses.

A duplicate email returns **409 `conflict`** with the generic message "Could not create an account with these details." The same message is used for any signup conflict, which limits account enumeration while keeping the UX simple. Login errors are always **401** `invalid_credentials` "Email or password is incorrect.", whether the email is unknown, the password is wrong or the account is inactive; an unknown email still costs one Argon2 verification.

### 2.3 Supplier profile

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/supplier` | S | Profile + computed `eligibility` | P0 |
| PUT | `/supplier` | S | Create or replace the profile | P0 |
| POST | `/supplier/udyam-certificate` | S | Multipart upload → evidence (`udyam_certificate`, no case); sets status `certificate_uploaded` | P0 |
| POST | `/supplier/verify-udyam` | S | Provider check (sandbox/simulated) → status + `mode` | P1 |

`GET /supplier` response:

```json
{
  "id": "…",
  "legal_name": "Ravi Fasteners",
  "udyam_number": "UDYAM-TS-02-0001234",
  "enterprise_class": "micro",
  "major_activity": "manufacturing",
  "udyam_registration_date": "2024-06-12",
  "udyam_verification_status": "certificate_uploaded",
  "gstin": "36ABCDE1234F1Z5",
  "contact_email": "ravi@example.in",
  "signatory_name": "Ravi Kumar",
  "signatory_designation": "Proprietor",
  "eligibility": {
    "verdict": "eligible",          // eligible | eligible_with_warnings | not_eligible | cannot_assess
    "reasons": [
      { "rule_id": "R9", "status": "met", "message": "Micro enterprise with Udyam registration." }
    ]
  }
}
```

### 2.4 Buyers

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/buyers?q=&include_archived=false&limit=&cursor=` | S | List/search by name or GSTIN | P0 |
| POST | `/buyers` | S | Create | P0 |
| GET | `/buyers/{buyer_id}` | S | Detail + case counts | P0 |
| PATCH | `/buyers/{buyer_id}` | S | Update contact fields | P0 |
| POST | `/buyers/{buyer_id}/archive` | S | Archive (no delete) | P0 |

Body: `{ "legal_name", "gstin"?, "contact_name"?, "email"?, "phone"?, "address"? }`. GSTIN is validated by format and checksum. A duplicate GSTIN for the same supplier returns **409 `conflict`**.

### 2.5 Cases

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases` | S | List with computed summary | P0 |
| POST | `/cases` | S | Create a case (log delivery) | P0 |
| GET | `/cases/{case_id}` | S | Full detail with `clock`, `amounts`, `checklist_summary`, `next_action` | P0 |
| PATCH | `/cases/{case_id}` | S | Edit invoice/delivery fields (only before any communication is approved) | P0 |
| POST | `/cases/{case_id}/close` | S | `{ "reason": "…" }` | P0 |
| POST | `/cases/{case_id}/reopen` | S | Reopen | P0 |
| GET | `/cases/{case_id}/interest?as_of=YYYY-MM-DD` | S | Full period table | P0 |
| GET | `/cases/{case_id}/checklist` | S | All items C01–C17 | P0 |
| GET | `/dashboard` | S | Needs-attention list + totals | P0 |

`GET /cases` query parameters:

- `lifecycle=open|closed|all` (default `open`)
- `acceptance_state=window_open|objection_raised|accepted`
- `payment_state=not_due|overdue|settled`
- `buyer_id`
- `q` (invoice number or buyer name)
- `sort=urgency|delivery_date_desc` (default `urgency`)
- `limit`, `cursor`

State filters are applied after computation (bounded per supplier; see DATABASE.md Section 4).

`POST /cases` request:

```json
{
  "buyer_id": "…",
  "invoice_number": "RF/26-27/118",
  "invoice_date": "2026-11-01",
  "invoice_amount": "500000.00",
  "description": "M8 hex bolts, 20,000 pcs",
  "delivery_date": "2026-11-01",
  "delivery_location": "Buyer plant gate, Patancheru",
  "deal_type": "verbal",               // verbal | written
  "agreed_payment_days": null,          // written only; 0–365
  "agreed_due_date": null               // written only; mutually exclusive with agreed_payment_days
}
```

`GET /cases/{case_id}` response (abridged):

```json
{
  "id": "…",
  "reference": "PS-2026-0042",
  "lifecycle": "open",
  "buyer": { "id": "…", "legal_name": "Apex Auto Components Pvt Ltd" },
  "invoice_number": "RF/26-27/118",
  "invoice_date": "2026-11-01",
  "invoice_amount": "500000.00",
  "delivery_date": "2026-11-01",
  "deal_type": "verbal",
  "recorded_late_days": 0,
  "rule_set_version": "msmed-v1",
  "clock": {
    "as_of": "2026-11-20",
    "acceptance_state": "accepted",                 // window_open | objection_raised | accepted
    "acceptance_basis": "deemed",                   // deemed | acknowledged | objection_removed | null
    "window_day": null,                             // 0–15 while window_open
    "window_end": "2026-11-16",
    "acceptance_date": "2026-11-01",
    "due_date": "2026-11-16",
    "interest_start": "2026-11-17",
    "indicative_limitation_date": "2029-11-17",
    "payment_state": "overdue",                     // not_due | overdue | settled | null
    "days_overdue": 4,
    "terms_capped_at_45": false,
    "explanations": [
      { "field": "acceptance_date", "rule_id": "R3", "text": "No written objection was recorded by Day 15, so the delivery date is treated as the day of acceptance." }
    ]
  },
  "amounts": {
    "as_of": "2026-11-20",
    "principal": "500000.00",
    "paid": "0.00",
    "outstanding_principal": "500000.00",
    "interest": "945.21",
    "total_claimable": "500945.21",
    "illustrative": true
  },
  "checklist_summary": { "required_met": 7, "required_total": 9, "warnings": 1 },
  "next_action": { "code": "send_demand", "title": "Send a demand letter" },
  "has_simulated_items": true
}
```

### 2.6 Buyer responses

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/responses` | S | List (each with computed `within_window`, `counts_as_written`) | P0 |
| POST | `/cases/{case_id}/responses` | S | Record a response | P0 |
| POST | `/cases/{case_id}/responses/{response_id}/remove-objection` | S | `{ "removed_on": "YYYY-MM-DD", "evidence_item_id"? }` | P0 |
| POST | `/cases/{case_id}/responses/eml` | S | Upload a `.eml` → evidence with DKIM result + a draft response prefilled (the supplier confirms the kind) | P1 |

`POST /cases/{case_id}/responses` request:

```json
{ "kind": "objection", "received_on": "2026-11-05", "channel": "email", "summary": "Buyer says 2,000 pcs had thread defects.", "evidence_item_id": "…" }
```

The response includes the updated `clock`.

### 2.7 Payments

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/payments` | S | List | P0 |
| POST | `/cases/{case_id}/payments` | S | `{ "amount", "received_on", "mode", "reference"?, "evidence_item_id"?, "confirm_exceeds_principal"? }` | P0 |
| POST | `/cases/{case_id}/payments/{payment_id}/void` | S | `{ "reason" }` | P0 |

### 2.8 Evidence

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/evidence?kind=&include_excluded=false` | S | List | P0 |
| POST | `/cases/{case_id}/evidence` | S | Multipart: `file`, `kind`, `note`?, `stated_captured_at`? | P0 |
| GET | `/evidence/{evidence_id}/download` | S | Stream the original bytes (`Content-Disposition: attachment`) | P0 |
| POST | `/evidence/{evidence_id}/exclude` | S | `{ "reason" }` | P0 |
| POST | `/cases/{case_id}/integrity-check` | S | Re-hash files + verify the chain; records the result in the timeline | P0 |

Upload response (201):

```json
{ "id": "…", "kind": "delivery_challan", "original_filename": "challan.jpg", "mime_type": "image/jpeg", "size_bytes": 1832211, "sha256": "9f2c41ab…e07d", "received_at": "2026-11-01T09:02:11.123Z", "excluded": false }
```

Upload rules:

- Allowed types (by magic bytes): PDF, JPEG, PNG, HEIC/HEIF, `message/rfc822` (`.eml`), UTF-8 plain text.
- Size ≤ `MAX_UPLOAD_MB`; total per case ≤ `MAX_CASE_STORAGE_MB`.
- A duplicate `(case, sha256)` returns **409 `duplicate_evidence`** with the existing item in `detail`.

Integrity-check response:

```json
{ "result": "pass", "checked_files": 9, "checked_events": 23, "mismatches": [], "timeline_head_hash": "…", "recorded_event_seq": 24 }
// on failure: "result": "fail", "mismatches": [ { "type": "file", "evidence_id": "…", "expected": "…", "actual": "…" } ]
```

### 2.9 Communications

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/communications` | S | List | P0 |
| POST | `/cases/{case_id}/communications` | S | `{ "kind": "delivery_intimation" \| "demand", "amounts_as_of"?, "buyer_share_link_id"? }` → draft from template | P0 |
| GET | `/communications/{communication_id}` | S | Detail including the rendered preview text | P0 |
| PATCH | `/communications/{communication_id}` | S | Edit `subject`, `body_text`, `to_email` (draft only) | P0 |
| POST | `/communications/{communication_id}/approve` | S | `{ "confirm": true, "content_sha256_seen": "…" }` → freeze + PDF | P0 |
| POST | `/communications/{communication_id}/send` | S | `{ "mode": "email" }` (uses `simulated` automatically when `EMAIL_MODE=simulated`; the response states the mode) | P0 |
| POST | `/communications/{communication_id}/record-manual` | S | `{ "sent_on", "evidence_item_id"? }` (`sent_on` is stored as `manual_sent_on`) | P0 |
| GET | `/communications/{communication_id}/pdf` | S | Download the approved PDF | P0 |

Rules:

- `demand` can only be created when `payment_state = overdue` (otherwise 409 `invalid_state`).
- `buyer_share_link_id` is accepted from Phase 10 onwards (IMPLEMENTATION_PLAN T10.8). Before that the field is not part of the schema.
- Communications are case-level only. Supplier-level evidence (Udyam certificate) creates no timeline event (DATABASE.md 3.9).
- Approval requires the signatory fields on the supplier profile (409 `profile_incomplete`).
- `content_sha256_seen` must match the server's hash of the current draft. This proves the supplier approved exactly what they saw. A mismatch returns 409 `conflict` ("The letter changed. Review it again.").
- `send` is accepted only from `approved` or `send_failed`; anything else returns 409 `already_sent` / `invalid_state`. An SMTP failure returns **502 `integration_failed`**, with status `send_failed` saved.

### 2.10 Timeline

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/timeline?order=desc&limit=&cursor=` | S | Events with hashes and actor labels | P0 |

### 2.11 Sealed packs

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/packs` | S | List versions | P0 |
| POST | `/cases/{case_id}/packs` | S | `{ "amounts_as_of"? }` → generate (synchronous; 409 `integrity_failed` with the report if verification fails) | P0 |
| GET | `/packs/{pack_id}/download` | S | ZIP stream | P0 |

Pack response:

```json
{ "id": "…", "version": 2, "manifest_sha256": "…", "size_bytes": 14820331, "amounts_as_of": "2026-11-20", "includes_simulated": true, "created_at": "…", "checklist_snapshot": { "required_met": 8, "required_total": 9 } }
```

#### Demo build: on-demand evidence pack export

`GET /cases/{case_id}/evidence-pack` (**supplier session required** since Phase 6; still mounted only when `APP_ENV` is not `production`). Read-only: it writes no database row and no timeline event.

- **200:** `application/zip`, `Content-Disposition: attachment; filename="PaySetu-evidence-pack-PS-YYYY-NNNN.zip"`, `Cache-Control: private, no-store`, `X-PaySetu-Pack-SHA256: <SHA-256 of manifest.json>`.
- **401:** no valid session. **404 `not_found`:** unknown case, or a case owned by another supplier. **409 `integrity_failed`:** a stored file or the timeline chain fails verification (also if a file changes while the pack is built); `errors[]` lists `file:<evidence id>` or `timeline:seq N` with the reason, and no pack is created. **409 `conflict`:** the case changed while the pack was being built. **429 `rate_limited`:** 5 per hour per case (keyed by supplier and case).
- **Contents:** `README_FIRST.md`, `01_case_summary.md`, `02_deemed_clock_and_interest.md`, `03_timeline.md`, `timeline.json`, `04_case_strength_checklist.md`, `05_verification_report.md`, `evidence/NN_<kind>_<hash8>.<ext>` (original bytes), `manifest.json` (path, size and SHA-256 of every other file; its own SHA-256 is the pack ID). Entry names are generated by PaySetu, never from user filenames. No Section 63 certificate (no counsel-reviewed template; LR-16).
- **Differences from the planned `POST /cases/{id}/packs` + `GET /packs/{id}/download`:** packs are not stored or versioned and there is no `sealed_packs` table; the pack ID is not recorded in the timeline.

### 2.12 Share links

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/cases/{case_id}/share-links` | S | List (no tokens) with status and view counts | P0 |
| POST | `/cases/{case_id}/share-links` | S | Create; the response includes `url` **once** | P0 |
| POST | `/share-links/{link_id}/revoke` | S | Revoke | P0 |
| GET | `/share-links/{link_id}/access-log` | S | Access entries (time, action, user-agent summary) | P0 |

Create request:

```json
// buyer cost link
{ "purpose": "buyer_cost", "expires_in_days": 90 }
// advocate link
{ "purpose": "advocate", "sealed_pack_id": "…", "recipient_name": "Adv. A. Sharma", "recipient_email": "a.sharma@example.in",
  "expires_in_days": 30, "consent": { "text_version": "advocate-share-v1", "accepted": true } }
```

Validation:

- `expires_in_days` must be 1–90 for buyer links and 1–30 for advocate links.
- A buyer link requires the case to have a fixed acceptance date.

Response (201): `{ "id": "…", "url": "https://<host>/a/<token>", "expires_at": "…" }`.

### 2.13 Public share endpoints (token holders)

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/public/share/{token}` | T | Purpose-specific projection | P0 |
| GET | `/public/share/{token}/pack` | T (advocate) | Download the linked pack version | P0 |
| POST | `/public/share/{token}/integrity-check` | T (advocate) | Run verification (rate-limited); logged as an `advocate_link` timeline event | P0 |

Public endpoints need no CSRF header (they are token-authenticated and have no cookies). They respond with `Cache-Control: no-store`, `X-Robots-Tag: noindex, nofollow` and `Referrer-Policy: no-referrer`.

**Buyer projection:**

```json
{
  "purpose": "buyer_cost",
  "supplier": { "legal_name": "Ravi Fasteners", "udyam_number": "UDYAM-TS-02-0001234", "contact_email": "ravi@example.in", "contact_phone": "+91…" },
  "buyer": { "legal_name": "Apex Auto Components Pvt Ltd" },
  "invoice": { "number": "RF/26-27/118", "date": "2026-11-01", "amount": "500000.00" },
  "dates": { "delivery_date": "…", "acceptance_date": "…", "acceptance_basis": "deemed", "due_date": "…", "interest_start": "…" },
  "amounts": { "as_of": "…", "outstanding_principal": "…", "interest": "…", "total": "…", "illustrative": true },
  "legal_notes": [ { "rule_id": "R8", "title": "Interest on late payment", "text": "…" }, { "rule_id": "R13", "…": "…" }, { "rule_id": "R14", "…": "…" } ],
  "expires_at": "…",
  "simulated": false
}
```

It never includes evidence, the timeline, other cases or any bank details.

**Advocate projection:** case summary (as for a supplier, without `next_action`), the timeline (all events), the evidence metadata list (kind, filename, size, sha256, received_at, excluded), pack metadata, the consent statement (`shared_by`, `shared_with`, `shared_on`) and `expires_at`. Individual evidence files are available only inside the pack.

### 2.14 Reference

| Method | Path | Auth | Purpose | P |
| --- | --- | --- | --- | --- |
| GET | `/reference/bank-rates` | S | Rate history with sources and table version | P0 |
| GET | `/reference/rule-set` | S | Current rule-set version, rule IDs and explanation text | P0 |

### 2.15 Account data (P1)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/account/export` | S | Build and return a ZIP: profile JSON + the latest pack for each case (generated as needed) |
| POST | `/account/deletion-request` | S | `{ "confirm_email": "…" }`: marks the account inactive, revokes all sessions and links; the operator completes deletion per the retention policy (PRD D12) |

---

## 3. Validation Summary

| Field | Rule |
| --- | --- |
| Email | RFC-valid, lowercased, ≤ 254 |
| Password | 10–128 chars, not common |
| Udyam number | `^UDYAM-[A-Z]{2}-\d{2}-\d{7}$` |
| GSTIN | 15 chars, `^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$` + checksum |
| PIN code | 6 digits, first digit not 0 |
| Money | Decimal string, ≤ 2 decimals, > 0, ≤ 10,00,00,00,000.00 (Rs 1,000 crore) |
| Dates | Valid ISO date; delivery/response/payment dates not in the future (IST); response and payment dates ≥ delivery date |
| Agreed payment days | Integer 0–365 (a value over 45 is accepted but capped by the clock with a note) |
| Free text | Trimmed; length limits per DATABASE.md; control characters stripped |
| Enum fields | Exact values listed in DATABASE.md |

---

## 4. External APIs and Integrations

| Integration | Direction | MVP | Operations | Failure handling |
| --- | --- | --- | --- | --- |
| SMTP | Outbound | P0 | Send one message (approved communication, or a password reset in P1) with the PDF attached | 15 s timeout; no automatic retry; status `send_failed` + sanitised reason; the user can retry or use manual mode |
| Simulated email | — | P0 | No network; marks the communication sent with `delivery_mode=simulated` | n/a |
| Udyam/GSTIN verification (Cashfree Secure ID or similar) | Outbound | P1 (sandbox) | Verify a Udyam number → name, class, registration date | 10 s timeout; one retry on network error; result stored with `mode=sandbox` and labelled "simulated" in the UI; a provider error never blocks the supplier |
| DKIM (DNS) | Outbound DNS | P1 | Look up the selector key during `.eml` verification | DNS failure → `dkim_result=error`, upload still succeeds |

**Message content rules (email):**

- From: `EMAIL_FROM` (platform domain). Reply-To: the supplier's `contact_email`.
- The subject and body are exactly the approved content. The PDF is attached. The footer states "Sent via PaySetu on behalf of [supplier legal name]."
- No tracking pixels or link rewriting.

### Webhooks

**None in MVP.** Buyer replies arrive via manual recording or `.eml` upload (P1).

Future inbound webhooks (inbound email parsing, eSign callbacks) must:

1. live under `/api/v1/webhooks/{provider}`
2. verify the provider's HMAC signature over the raw body with a constant-time comparison
3. reject timestamps older than 5 minutes
4. be idempotent by provider event ID
5. return 2xx quickly and never trust the payload for ownership

---

## 5. Rate Limiting

| Scope | Limit | Key |
| --- | --- | --- |
| `POST /auth/login` | 5/min and 20/hour | IP + email; IP |
| `POST /auth/signup` | 5/hour (`AUTH_SIGNUP_LIMIT_PER_HOUR`; production refuses a higher value) | IP |
| `POST /auth/password/forgot` (P1) | 3/hour | IP + email |
| `/public/share/*` | 60/min; 10 invalid tokens/min | IP |
| `POST /cases/{id}/evidence` | 30/min | user |
| `POST /communications/{id}/send` | 10/hour | user |
| `POST /cases/{id}/packs` | 5/hour | case |
| `POST …/integrity-check` | 10/hour | case (supplier and advocate combined) |
| Everything else (S) | 300/min | user |

Exceeding a limit returns **429** with `Retry-After`. Limits are in-memory (single instance; ARCHITECTURE.md Section 8.5).

---

## 6. Environment Variables

Authoritative list: ARCHITECTURE.md Section 12. The API depends on:

| Variable | Used for |
| --- | --- |
| `APP_ENV` | Production gate, OpenAPI exposure, demo seed guard |
| `PUBLIC_BASE_URL` | Share URLs, CSRF origin check, email links |
| `DATABASE_URL`, `STORAGE_DIR` | Persistence |
| `TOKEN_HASH_KEY` | Share-token and IP HMAC |
| `SESSION_IDLE_HOURS`, `SESSION_ABSOLUTE_DAYS` | Sessions |
| `MAX_UPLOAD_MB`, `MAX_CASE_STORAGE_MB` | Upload limits |
| `EMAIL_MODE`, `SMTP_*`, `EMAIL_FROM` | Email adapter |
| `VERIFICATION_MODE`, `CASHFREE_*` | Verification adapter (P1) |
| `ALLOW_NONLIVE_VERIFIED` | Permit simulated adapters in production (forces the banner) |
| `LOG_LEVEL` | Logging |

No variable is exposed to the browser. The frontend learns the adapter modes only through `GET /auth/me` and `GET /health`.

---

## 7. Data Privacy and Failure Handling

| Concern | Rule |
| --- | --- |
| Minimum exposure | Each endpoint returns only the fields its screen needs. Share projections are explicit allowlists |
| Tokens | Raw share tokens appear only in the create response. They are never logged (paths are logged with the token replaced by `{token}`) |
| Downloads | `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store` |
| Logs | No request or response bodies; no file contents; IPs hashed |
| Partial failure | Uploads: the file is written first, then the row; a failure after writing leaves an unreferenced file, never a dangling row. Sends: the approval is persisted before any network call |
| Provider outage | The feature degrades to manual mode (send it yourself) or "unverified" status; core case flow never blocks on an external service |
| Clock skew | All legal-date computation uses the server's Asia/Kolkata date. The client time is never used |
| Simulated data | Any response containing simulated outcomes carries `"simulated": true` / `"mode": "simulated"`, and the UI must render the label |
