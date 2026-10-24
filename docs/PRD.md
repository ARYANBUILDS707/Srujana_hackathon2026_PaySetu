# PaySetu: Product Requirements Document (PRD)

| Field | Value |
| --- | --- |
| Product | PaySetu (earlier working title: ProofFirst) |
| Problem statement | LS-03: Paid on Time, by Law (Srujana Tech Fest 2026, Legal Services track) |
| Document status | Draft v1.1 (consistency review, 25 Oct 2026), awaiting owner approval |
| Source material | *LS03_Final_Ideathon_Document* (24 Oct 2026), based on ideation document v12 |
| Role of this document | Source of truth for product scope. DESIGN, ARCHITECTURE, DATABASE, API and AGENTS documents derive from it |

> **Not legal advice.** PaySetu prepares and organises evidence. Every statutory rule in this document is the team's reading of the law and must be confirmed by a qualified advocate before real use. Rules marked **[COUNSEL]** must not be presented as settled law in the product.

### Conventions used in this document

- **[ASSUMPTION]**: a choice made to fill a gap in the source material. It can be changed without redesign.
- **[DECISION Dx]**: needs explicit owner approval. All decisions are collected in [Section 16](#16-decisions-requiring-approval).
- **[COUNSEL]**: a legal reading that needs advocate confirmation.
- **P0** = MVP must-have, **P1** = MVP if time allows, **Later** = out of MVP.
- "Day N" = N calendar days after the delivery date (delivery date = Day 0). All legal dates use the Asia/Kolkata calendar.

---

## Table of Contents

1. [Problem](#1-problem)
2. [Value Proposition](#2-value-proposition)
3. [Target Users and Personas](#3-target-users-and-personas)
4. [Legal Rules the Product Encodes](#4-legal-rules-the-product-encodes)
5. [Core User Journeys](#5-core-user-journeys)
6. [User Stories](#6-user-stories)
7. [Features and Functional Requirements](#7-features-and-functional-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Pages and Screens](#9-pages-and-screens)
10. [Roles and Permissions](#10-roles-and-permissions)
11. [Data Requirements](#11-data-requirements)
12. [Integrations](#12-integrations)
13. [Loading, Empty and Error States](#13-loading-empty-and-error-states)
14. [MVP Scope and Out of Scope](#14-mvp-scope-and-out-of-scope)
15. [Success Criteria](#15-success-criteria)
16. [Decisions Requiring Approval](#16-decisions-requiring-approval)
17. [Open Legal Questions for Counsel](#17-open-legal-questions-for-counsel)

---

## 1. Problem

Indian micro and small enterprises (MSEs) are routinely paid late by larger buyers. The ideation research cites over Rs 10.7 lakh crore locked in delayed payments and about 80% of MSME invoices paid late. Both figures come from secondary sources.

The MSMED Act 2006 already protects these suppliers:

- payment within an agreed period of at most 45 days from the **day of acceptance**, or within 15 days if there is no written agreement
- compound interest at three times the RBI bank rate, with monthly rests, on late payment
- a low-cost dispute route: the MSE Facilitation Council and, since 15 Oct 2025, the MSME ODR portal

**The core problem:** every one of these rights is counted from the day of acceptance, and informal suppliers cannot prove it. Their orders are verbal, their messages are on WhatsApp and their challans are loose paper. Most do not know that if the buyer raises no written objection within 15 days of delivery, the delivery day becomes the day of acceptance. By the time a dispute starts, the evidence is scattered, unverifiable or lost.

Existing tools each cover a single job: delivery proof (ePOD tools), reminders (Vyapar), buyer-side compliance (Tally, Zoho), notices (Vasuli) or filing (the ODR portal). None of the tools reviewed turns delivery proof into dated, tamper-evident evidence tied to the MSMED Act before a dispute begins.

## 2. Value Proposition

**For the supplier:** "Log a delivery in under a minute. PaySetu tells you the legal acceptance date, the due date and the interest owed, keeps tamper-evident proof, and hands you a ready-to-file pack if the buyer does not pay."

| Supplier pain | PaySetu answer | Module |
| --- | --- | --- |
| "I can't prove when the buyer accepted the goods." | Records delivery, sends an approved delivery intimation, tracks the 15-day objection window, fixes the acceptance date | DeemedClock |
| "My proof is screenshots and paper." | SHA-256 hash and server timestamp on every file; hash-chained timeline; tamper detection | Evidence Vault |
| "I don't know if my case is strong enough to file." | Rule-based readiness checklist with one-line fixes. It does not predict outcomes | Case Strength |
| "The buyer doesn't take delay seriously." | Shareable page showing statutory interest, the 75% pre-deposit rule and the 43B(h) tax effect | Buyer Cost Page |
| "Filing or briefing a lawyer means collecting everything again." | One sealed export with manifest, timeline and a draft s.63 certificate; consent-based advocate link | Sealed Pack |

**What PaySetu is not:** a law firm, collection agency, lawyer marketplace, credit-bureau reporter, filing agent or government portal. It never promises recovery, never contacts a buyer without the supplier's approval, and never takes money from lawyers.

## 3. Target Users and Personas

| Persona | Description | Primary needs | Device context |
| --- | --- | --- | --- |
| **Ravi: micro manufacturer (primary)** | Owner of a small fastener unit; Udyam-registered; sells on verbal orders to 5–20 larger buyers; limited legal knowledge; comfortable with WhatsApp, not with forms | Fast delivery logging at the gate; clear "what do I do next"; plain-language dates and amounts | Mid-range Android phone, intermittent 4G |
| **Meena: small services firm (primary)** | Runs a small IT or maintenance services firm with written purchase orders and 30–60 day terms; has an accountant | Accurate due date and interest; demand notice; a pack to hand to an advocate | Laptop and phone |
| **Advocate (secondary, external)** | Engaged by the supplier to file or conciliate | Organised, verifiable evidence; timeline; draft s.63 certificate; no account to create | Laptop |
| **Buyer's finance team (secondary, external)** | Accounts payable at the buying company | A clear statement of the amount, due date and statutory consequences | Laptop, opened from an email link |
| **CA / accountant (future channel)** | Advises supplier clients | Multi-client access (Later) | Laptop |

**Eligibility boundary:** the payment protections in ss.15–24 apply only to micro and small enterprises with a valid Udyam registration. Medium enterprises are out of scope. PaySetu lets any supplier create an account, but it flags ineligibility clearly (see FR-SUP-04).

## 4. Legal Rules the Product Encodes

These rules drive DeemedClock, the interest calculator and the checklist. They must be implemented as **versioned, configurable rules** (rule set `msmed-v1`), not scattered constants. Every output records the rule-set version that produced it. Rule IDs are stable. New rules get new IDs.

### 4.1 Classification

| Tier | Meaning | Who can change it |
| --- | --- | --- |
| **S: statute text checked** | The wording was compared with the text of the MSMED Act 2006 as enacted (PRS India copy, checked 25 Oct 2026). It has **not** been checked for later amendments or against the current India Code consolidation. Counsel still confirms how it applies | Only a statutory change or counsel advice |
| **I: interpretation, counsel review required** | A reading of the statute, case law or secondary sources that the product depends on. The product uses it as a labelled default and never states it as settled law | Counsel advice, recorded in DECISIONS.md |
| **C: configurable product assumption** | A calculation or product choice where the law is silent or ambiguous. It is set in the rule set or configuration | Owner approval (DECISIONS.md), with counsel review where noted |

### 4.2 Statute text (tier S)

| ID | Rule | Basis |
| --- | --- | --- |
| R1 | **Day of acceptance** = the day of the actual delivery of goods or the rendering of services. | MSMED Act s.2(b), Explanation (i)(a) |
| R2 | Where the buyer objects **in writing** regarding acceptance **within fifteen days** from delivery, the day of acceptance = the day the supplier removes the objection. | s.2(b), Explanation (i)(b) |
| R3 | **Deemed acceptance:** where no written objection is made within fifteen days from delivery, the day of deemed acceptance = the day of actual delivery. | s.2(b), Explanation (ii) |
| R4 | **Appointed day** = the day following immediately after the expiry of fifteen days from the day of acceptance or deemed acceptance. | s.2(b) |
| R5 | **No written agreement:** the buyer must pay before the appointed day. | s.15 |
| R6 | **Written agreement:** the buyer must pay on or before the agreed date, and the agreed period may not exceed 45 days from the day of acceptance or deemed acceptance. | s.15 proviso |
| R7 | **Interest start:** from the appointed day, or from the date immediately following the agreed date. | s.16 |
| R8 | **Interest:** compound interest with monthly rests, at three times the bank rate notified by the Reserve Bank, notwithstanding any agreement. | s.16 |
| R9 | **Supplier** = a micro or small enterprise that has filed a memorandum with the authority under s.8. (That Udyam registration now serves this role comes from later notifications. Tier I, not verified.) *Amendment Act 2026 s.5 substitutes s.8 (free, voluntary registration on a national digital platform; reported in force 15 Oct 2026) while s.2(n) is unchanged: see LR-23.* | s.2(n) |
| R13 | **Pre-deposit:** a court will not entertain an application to set aside a Council award unless the appellant (not being a supplier) deposits 75% of the awarded amount. *Amendment Act 2026 s.10 substitutes s.19 (adds mediated settlements and a 50% payout after 6 months); not yet commenced, so the current text applies: see LR-25.* | s.19 |

### 4.3 Interpretations requiring counsel review (tier I)

| ID | Interpretation | Basis / source | Product use |
| --- | --- | --- | --- |
| R3a | An objection received **after** Day 15 does not move the acceptance date. | Follows from the text of R2/R3; Taxmann FAQ | Recorded and labelled "outside window" |
| R4a | **Day counting:** "fifteen days from" excludes the delivery day (General Clauses Act 1897 s.9). So: Day 0 = delivery, the window ends on Day 15, the appointed day is Day 16, the verbal-deal due date is Day 15, and interest runs from Day 16. | General Clauses Act s.9; ideation correction note | DeemedClock arithmetic |
| R4b | No adjustment when Day 15 or the due date falls on a Sunday or public holiday. | The statute is silent | DeemedClock arithmetic |
| R6a | Written terms longer than 45 days are treated as **capped at 45 days**, not as void. | Reading of the s.15 proviso | Cap with a visible note |
| R9a | Udyam registration (from July 2020) satisfies the s.2(n) memorandum requirement. | MSME notification 26 June 2020 (not verified here) | Eligibility check |
| R10 | Supplies made before the Udyam registration date may not get the benefits (*Silpi Industries v. KSRTC*, 2021). | Case law | Checklist warning only |
| R11 | Retail and wholesale traders registered on Udyam may be limited to priority-sector lending and may not get the delayed-payment protections. | Ministry of MSME OM, 2 July 2021 (not verified here) | Checklist warning only |
| R12 | Limitation is generally 3 years from when payment falls due. | Limitation Act; *Silpi Industries* | Indicative date only |
| R14 | The buyer's deduction for dues to micro and small enterprises paid beyond the s.15 limit is deferred to the year of payment. | Income-tax Act 1961 s.43B(h); 2025 Act numbering not verified | Informational text only |
| R15 | Electronic evidence needs a BSA 2023 s.63 certificate (with hash values per the Schedule). Screenshots alone are weak. | BSA 2023 s.63; Schedule not checked against the Gazette | Draft certificate, watermarked |
| R16 | No statutory demand notice is required; a notice is evidence, not a precondition. | Ideation doc v12 | Demand letter is optional |
| R19 | **"In writing"** includes email, letter, WhatsApp/SMS/chat messages and written notes. A phone call or oral objection is not writing. | Reading of s.2(b) | FR-CLK-10 |
| R20 | A buyer's acknowledgement within the window does not end the window early. | Conservative reading | FR-CLK-08 |
| R21 | With several in-window written objections, acceptance = the day the **last** of them is removed. | Reading of s.2(b)(i)(b) | DeemedClock |

### 4.4 Configurable assumptions (tier C)

| ID | Assumption (default) | Decision | Counsel review |
| --- | --- | --- | --- |
| A1 | Monthly rests are counted from the interest start date. Each complete month accrues outstanding × (annual rate ÷ 12). A final partial month accrues pro rata at days ÷ 365. | D3 → LR-12 | Yes |
| A2 | Amounts are rounded half-up to the paisa at each monthly rest. | D3 → LR-12 | Yes |
| A3 | The rate for each monthly period = 3 × the RBI bank rate in force on that period's first day. | D5 → LR-13 | Yes |
| A4 | Part payments are allocated to principal first (conservative). | D4 → LR-14 | Yes |
| A5 | Legal dates use the Asia/Kolkata calendar date. | ADR-012 | No |
| A6 | A response with channel `other` is treated as written (conservative: it can only stop the clock, never inflate a claim). | LR-04 | Yes |
| A7 | Indicative limitation date = interest start + 3 years; the checklist warns 180 days before. | LR-11 | Yes |
| A8 | One case = one invoice = one delivery date. | ADR-021 | No |
| A9 | Written terms given as "N days" are counted from the day of acceptance. A stated agreed date is used as given. | LR-22 | Yes |
| A10 | Interest accrues for each day from the interest start date **through** the as-of date (inclusive). A payment reduces the balance from its own date. A monthly period that is cut short by the as-of date, or split by a payment, accrues each segment at days ÷ 365 instead of rate ÷ 12. | D3 → LR-12 | Yes |
| A11 | Indicative limitation date = interest start + 3 calendar years. If that date would be 29 Feb in a non-leap year, it becomes 28 Feb (the earlier date, which is conservative). | LR-11 | Yes |

All rule metadata (tier, source, effective date, verification status, decision reference) lives in `backend/app/rules/msmed-v1.toml`. That rule set encodes the MSMED Act 2006 text. The MSMED (Amendment) Act 2026 (Act 16 of 2026) was reviewed on 25 Oct 2026 from the Bill text and the PIB summary. It does **not** amend ss.2(b), 15, 16 or 17, so no calculation rule changes. Its other changes (s.8, new s.15A, ss.18–19) are tracked as LR-21 and LR-23 to LR-25 in [DECISIONS.md](DECISIONS.md), and every computed output lists them as pending reviews.

Every tier I and C item is listed in `docs/DECISIONS.md`, with its review status.

**Worked example (verbal deal, buyer silent).** Delivery on 1 Nov 2026 (Day 0):

- The objection window runs to 16 Nov (Day 15).
- Acceptance date = 1 Nov (deemed).
- Due date = 16 Nov (Day 15).
- Interest starts 17 Nov (Day 16).
- The indicative limitation date is about 17 Nov 2029.

This corrects the "15 days after deemed acceptance" wording in doc v12, consistent with the correction note in the final ideation document.

**Interest reference fixture.** Principal Rs 5,00,000 at a flat 17.25% (3 × 5.75%), compounded monthly at rate/12 for 12 complete months, gives interest of **Rs 93,407** (±Re 1 rounding). This matches the ideation document's chart. Required as a regression test.

## 5. Core User Journeys

### J1: Onboard (P0)

1. The supplier signs up with email and password [DECISION D2].
2. They enter their business profile: legal name, Udyam number, enterprise class, major activity, Udyam registration date, GSTIN (optional), address and contact details.
3. They upload a Udyam certificate (optional but recommended).
4. PaySetu shows an eligibility summary: "Eligible", "Eligible, with warnings" or "Not eligible for MSMED payment protections", with the reason.
5. The supplier accepts the Terms and Privacy Notice (DPDP consent) and reaches the dashboard.

### J2: Log a delivery at the gate (P0, core)

1. From the dashboard or the mobile "+" button, the supplier opens **New delivery**.
2. They pick or quickly create a buyer (name + email are enough to start).
3. They enter the invoice number, invoice date, amount and delivery date (defaults to today), and choose the deal type: verbal (no written terms) or written terms (agreed days or agreed date).
4. They take a photo of the signed challan or upload the invoice. The file is hashed on upload.
5. They save. The case is created and DeemedClock shows "Day 0 of 15".
6. Target: complete in 60 seconds or less on a phone. The ideation aspiration is about 20 seconds.

### J3: Send the delivery intimation (P0)

1. PaySetu prepares a delivery intimation draft (letter text + PDF) addressed to the buyer.
2. The supplier reviews and edits the draft, then explicitly **approves** it. The approved content is hashed and frozen.
3. The supplier picks a send mode: **Send by email from PaySetu** (or simulated in demo mode), or **I sent it myself**, with an optional proof upload (e.g. a WhatsApp export or a courier receipt).
4. The timeline records the approval and the send.

### J4: Track the 15-day window and record buyer responses (P0)

1. The case page shows the day strip (Day 0–15), the days remaining and the current state.
2. When the buyer replies, the supplier records the response:
   - type: objection, acknowledgement or other
   - date received
   - channel
   - summary
   - optional evidence (email file, screenshot, letter photo)
3. **Objection within the window:** the clock state becomes "Objection raised". The checklist flags it. When the issue is fixed, the supplier records "Objection removed on [date]" with evidence. That date becomes the acceptance date.
4. **No objection by end of Day 15:** from Day 16 onwards, the case shows "Deemed accepted on [delivery date]", plus the due date and the interest start date.
5. **Objection after Day 15:** it is recorded and labelled "received after the 15-day window". It does not change the acceptance date (R3a) [COUNSEL].

### J5: Payment due, overdue and demand (P0)

1. The case shows the due date and a countdown.
2. After the due date, the case is **Overdue**. PaySetu shows illustrative interest accrued to today and the total claimable amount, with the calculation table.
3. The supplier records part or full payments as they arrive.
4. The checklist flags "Demand not served". The supplier generates a **demand letter** draft that includes the amounts and, optionally, a link to the Buyer Cost Page. It goes through the same approve-then-send flow as J3.

### J6: Buyer Cost Page (P0)

1. The supplier creates a buyer-facing share link (it can also be embedded in the demand letter).
2. The buyer opens the link. No login is needed. The page shows:
   - invoice details and the acceptance basis
   - due date and days overdue
   - illustrative interest to date
   - plain-language notes on s.16, s.19 and s.43B(h)
   - a disclaimer
3. The page shows no evidence files and no supplier data beyond what is listed.
4. The supplier can revoke the link at any time. Views are logged.

### J7: Readiness check (P0)

1. The case's **Checklist** tab lists each requirement with its status (met, missing, warning or not applicable) and a one-line action.
2. The supplier works through the items, for example uploading a purchase order or recording a demand.

### J8: Export the Sealed Pack and share with an advocate (P0)

1. The supplier clicks **Generate Sealed Pack**. PaySetu runs an integrity check, then builds a versioned ZIP containing:
   - case summary
   - timeline
   - evidence
   - communications
   - draft s.63 certificate
   - counsel questions
   - hash manifest
2. The supplier downloads the pack to file on the ODR portal themselves.
3. Optionally, the supplier creates an **advocate link**: they name the advocate, confirm consent, choose an expiry (default 30 days) and copy the link to send. They can revoke it at any time and see every access.

### J9: Verify integrity (P0)

1. The supplier, or an advocate through the link, runs **Verify integrity**.
2. PaySetu re-hashes every stored file and re-walks the timeline chain.
3. It reports either "All N files and M timeline entries match their recorded hashes" or exactly which item does not match.
4. Demo: a modified file is flagged.

## 6. User Stories

Each story has acceptance criteria (AC). Stories are tagged with priority.

### Account and profile

- **US-01 (P0)** As a supplier, I can create an account and sign in, so my cases are private to me.
  - AC: email + password (minimum 10 characters); generic error on failed login; session persists for 7 days of activity; logout invalidates the session server-side.
- **US-02 (P0)** As a supplier, I can enter my Udyam and business details, so PaySetu can check eligibility.
  - AC: the Udyam number format is validated (`UDYAM-XX-00-0000000`); class and activity are required; an eligibility summary is shown with reasons.
- **US-03 (P1)** As a supplier, I can reset a forgotten password by email.
  - AC: single-use token, expires in 30 minutes, does not reveal whether the email exists.

### Buyers

- **US-04 (P0)** As a supplier, I can add and edit buyers with name, GSTIN (optional), contact person, email and phone.
  - AC: buyer email is required before an intimation can be sent by email; GSTIN format is validated when present.

### Deliveries and cases

- **US-05 (P0)** As a supplier, I can log a delivery with invoice details and a photo in under 60 seconds on my phone.
  - AC: the minimum required fields are buyer, invoice number, invoice date, amount, delivery date and deal type; the camera capture opens directly on mobile; the case is created even if the upload is still in progress; the timeline records "Delivery recorded".
- **US-06 (P0)** As a supplier, I can record a delivery that happened earlier (backdated).
  - AC: the delivery date can be in the past (not in the future); if it is more than 2 days before the record date, the timeline labels the entry "recorded N days after delivery" and so does the pack.
- **US-07 (P0)** As a supplier, I can see a list of my cases sorted by urgency, with filters by state and buyer.
  - AC: default sort is overdue first, then window closing soonest; search by invoice number or buyer name.

### DeemedClock

- **US-08 (P0)** As a supplier, I can see where each delivery stands in the 15-day objection window.
  - AC: the day strip shows Day 0–15 with today highlighted; it shows "N days left for the buyer to object"; after Day 15 it shows the acceptance basis and date.
- **US-09 (P0)** As a supplier, I can record a buyer objection, acknowledgement or other reply, with its date and evidence.
  - AC: an objection dated on or before Day 15 sets the state to Objection raised; one dated after Day 15 is stored and labelled "outside window" without changing acceptance; every response creates a timeline event.
- **US-10 (P0)** As a supplier, I can mark an objection as removed and attach proof.
  - AC: the removal date must be on or after the objection date; the acceptance date becomes the removal date; the due date and interest start are recalculated.
- **US-11 (P0)** As a supplier, I can see the due date and the interest start date, with the legal basis explained in plain words.
  - AC: written terms beyond 45 days are capped at 45, with a visible note; each date shows a "Why this date?" explanation citing the rule ID.

### Communications

- **US-12 (P0)** As a supplier, I can generate, edit, approve and send a delivery intimation.
  - AC: nothing is sent without an explicit approve action; approved text cannot be edited (a new version must be created); the PDF and the email body match the approved text; send failures are shown with a retry.
- **US-13 (P0)** As a supplier, I can record that I sent a communication myself, attaching proof.
  - AC: the send mode is stored as "manual"; any uploaded proof is hashed into the evidence vault.
- **US-14 (P0)** As a supplier, I can generate a demand letter after the due date, including amounts and an optional Buyer Cost Page link.
  - AC: the demand is available only when the case is overdue; amounts are as of a chosen date; the same approval flow as US-12 applies.

### Evidence Vault

- **US-15 (P0)** As a supplier, I can upload evidence files of defined types and see each file's hash and upload time.
  - AC: allowed types are PDF, JPEG, PNG, HEIC, EML and TXT; max 15 MB per file [DECISION D11]; the original bytes are stored unchanged; a duplicate file in the same case is detected and not stored twice.
- **US-16 (P0)** As a supplier, I can mark a wrongly uploaded file as excluded, with a reason, without deleting it.
  - AC: excluded files stay in the vault and the timeline; they are left out of new packs by default; the exclusion is a timeline event.
- **US-17 (P0)** As a supplier or advocate, I can verify that no evidence or timeline entry has changed.
  - AC: the report lists mismatches by item; the result is recorded in the timeline.
- **US-18 (P1)** As a supplier, I can upload a buyer's email as a `.eml` file and see whether its DKIM signature verifies.
  - AC: the result is shown as Verified, Failed or Not signed, with a plain explanation; the raw file is preserved.

### Case Strength

- **US-19 (P0)** As a supplier, I can see a readiness checklist with clear next actions.
  - AC: items follow FR-CHK-02; the summary reads "N of M required items complete"; the checklist never shows a win probability or score.

### Buyer Cost Page

- **US-20 (P0)** As a supplier, I can create, copy and revoke a buyer-facing link.
  - AC: the token is unguessable (128+ bits); it is stored hashed; expiry defaults to 90 days [ASSUMPTION]; revocation takes effect immediately; views are logged.
- **US-21 (P0)** As a buyer, I can open the link and understand what is owed and why.
  - AC: the page is readable without login; it shows an "as of" date; it shows no evidence files; it is marked noindex.

### Sealed Pack and advocate access

- **US-22 (P0)** As a supplier, I can generate and download a versioned Sealed Pack.
  - AC: the pack contents follow FR-PACK-02; the manifest hash is shown in the UI; regenerating creates a new version and never overwrites an old one.
- **US-23 (P0)** As a supplier, I can share a specific pack version with an advocate I choose, through a consent-based, expiring, revocable link.
  - AC: an explicit consent checkbox with text is required; expiry is 1–30 days (default 30); access is logged; the supplier can view the log.
- **US-24 (P0)** As an advocate, I can open the link, read the case summary and timeline, and download the pack.
  - AC: read-only; no account needed; an expired or revoked link shows a clear message.

### Privacy

- **US-25 (P1)** As a supplier, I can export all my data and request deletion of my account.
  - AC: the export is a ZIP of all cases (as packs) plus profile JSON; deletion follows the retention rule [DECISION D12].

## 7. Features and Functional Requirements

### 7.1 Accounts and supplier profile

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-AUTH-01 | Email + password sign-up and sign-in; passwords hashed with a modern memory-hard algorithm. | P0 |
| FR-AUTH-02 | Server-side sessions with idle expiry (7 days) and logout. | P0 |
| FR-AUTH-03 | Password reset by email. | P1 |
| FR-SUP-01 | One supplier profile per account in MVP [DECISION D14]. | P0 |
| FR-SUP-02 | Profile fields: legal name, trade name, Udyam number, enterprise class (micro / small / medium), major activity (manufacturing / services / trading), Udyam registration date, GSTIN, address, state, PIN, contact email and phone, authorised signatory name and designation. | P0 |
| FR-SUP-03 | Udyam verification status, one of: `self_declared`, `certificate_uploaded`, `provider_verified_sandbox`, `provider_verified_live`. Sandbox results must be labelled "simulated". | P0 (first two), P1 (provider) |
| FR-SUP-04 | Eligibility evaluation. Class = medium → "Not eligible". Activity = trading → warning (R11). A missing Udyam number → "Cannot assess". | P0 |

### 7.2 Buyers

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-BUY-01 | Create, edit and list buyers scoped to the supplier. | P0 |
| FR-BUY-02 | Validate GSTIN format when provided; email is required to send by email. | P0 |
| FR-BUY-03 | A buyer with cases cannot be deleted (it can be archived). | P0 |

### 7.3 DeemedClock

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-CLK-01 | A case represents **one invoice with one delivery date** [ASSUMPTION; partial deliveries are Later]. | P0 |
| FR-CLK-02 | Case fields: buyer, invoice number, invoice date, invoice amount (INR), goods/services description, delivery date, delivery location (optional), deal type (`verbal` or `written`), agreed payment days or agreed due date (written only). | P0 |
| FR-CLK-03 | The acceptance state is **computed from stored facts** (delivery date, responses, objection removal) on every read, using rule set `msmed-v1`. It is never stored as a mutable status. | P0 |
| FR-CLK-04 | Acceptance states: `window_open`, `objection_raised`, `accepted`. `accepted` carries a basis: `deemed` (no objection), `acknowledged` (buyer acknowledged within the window and no objection) or `objection_removed`. | P0 |
| FR-CLK-05 | Payment states: `not_due`, `overdue`, `settled` (outstanding principal = 0). Undefined while acceptance is not fixed. | P0 |
| FR-CLK-06 | Output dates: window end (Day 15), acceptance date, due date, interest start date, indicative limitation date. Each comes with a rule ID and a plain-language explanation. | P0 |
| FR-CLK-07 | Written terms longer than 45 days are capped at 45, with a visible note (R6, R6a). | P0 |
| FR-CLK-08 | A buyer acknowledgement does not end the window early. The state shows "Acknowledged, window still open" until Day 15 passes (R20) [COUNSEL]. | P0 |
| FR-CLK-09 | The case lifecycle (`open`, `closed`) is set by the supplier, and closing requires a reason. Closed cases are read-only except for reopening. | P0 |
| FR-CLK-10 | Only a **written** objection (email, letter, WhatsApp/chat message or written note handed over) received by Day 15 changes the clock. An objection recorded with channel "phone note" is stored and shown, but labelled "not in writing" and does not move acceptance. Channel "other" counts as written (R19, A6) [COUNSEL]. | P0 |
| FR-CLK-11 | With more than one in-window written objection, the state stays `objection_raised` until every one is removed. Acceptance = the latest removal date (R21) [COUNSEL]. No holiday adjustment is applied to any date (R4b). | P0 |

### 7.4 Interest calculator

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-INT-01 | Compute interest per R7–R8 and assumptions A1–A4, using exact decimal arithmetic. Money is stored in paise. | P0 |
| FR-INT-02 | Default method [DECISION D3]: monthly rests counted from the interest start date; each complete month accrues outstanding × (annual rate ÷ 12) and is capitalised; a final partial month accrues pro rata at days ÷ 365; amounts are rounded half-up to the paisa at each rest. | P0 |
| FR-INT-03 | Rate source: a versioned table of RBI bank-rate history (effective-from date, rate, source URL, verified-by). The rate for each monthly period = 3 × the bank rate in force on that period's first day [DECISION D5]. | P0 |
| FR-INT-04 | Part payments reduce outstanding principal from the payment date [DECISION D4: default principal-first allocation; conservative]. | P0 |
| FR-INT-05 | Output: principal outstanding, interest to the as-of date, total, and a period-by-period table (period, days, rate, opening balance, interest, closing balance). | P0 |
| FR-INT-06 | Every figure is labelled "Illustrative. Based on rule set msmed-v1 and RBI rates as recorded on [date]. Confirm with counsel." | P0 |
| FR-INT-07 | The as-of date is selectable (default today; it cannot be before the interest start date). | P0 |

### 7.5 Evidence Vault

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-EV-01 | Upload files with a type tag: `invoice`, `delivery_challan`, `delivery_photo`, `purchase_order`, `written_terms`, `email`, `chat_export`, `tracking_record`, `udyam_certificate`, `buyer_response`, `payment_proof`, `communication_proof`, `other`. | P0 |
| FR-EV-02 | Compute SHA-256 over the **original bytes** on the server. Never alter, compress, resize or strip metadata from stored evidence. | P0 |
| FR-EV-03 | Record the server receipt time (authoritative), plus an optional supplier-stated capture time and a note. | P0 |
| FR-EV-04 | Content-type allowlist with magic-byte checks; size limit per file [D11]. | P0 |
| FR-EV-05 | Evidence is append-only. Files cannot be edited or deleted by users. A mistaken upload can be marked `excluded` with a reason (FR-EV-06). | P0 |
| FR-EV-06 | Exclusion is a timeline event, and excluded files are left out of new packs. | P0 |
| FR-EV-07 | Every case action writes a **hash-chained timeline event**: each event stores the hash of its own canonical content and the previous event's hash. | P0 |
| FR-EV-08 | Integrity verification re-hashes all files and re-walks the chain, reporting any mismatches by item. | P0 |
| FR-EV-09 | `.eml` upload with DKIM verification result (`pass`, `fail`, `none`, `error`). | P1 |
| FR-EV-10 | Trusted timestamping (RFC 3161). | Later |

### 7.6 Communications (intimation and demand)

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-COM-01 | Templates: `delivery_intimation` and `demand`. Templates are versioned and marked "draft wording pending advocate review" until approved [COUNSEL]. | P0 |
| FR-COM-02 | Lifecycle: `draft` → `approved` → (`sending`, transient) → `sent` / `send_failed` / `recorded_manual`. Only the supplier can approve. | P0 |
| FR-COM-03 | On approval: freeze the subject and body, render the PDF, hash both into the vault, write a timeline event. | P0 |
| FR-COM-04 | Send modes: `email` (SMTP), `simulated` (demo; clearly labelled, sends nothing) and `manual` (the supplier sent it themselves). | P0 |
| FR-COM-05 | A communication can be sent at most once. A failed send can be retried; a sent one cannot be re-sent (create a new communication instead). | P0 |
| FR-COM-06 | Signatory: the letter shows the supplier's authorised signatory name and designation. Digital signing (eSign/DSC) is Later. | P0 |
| FR-COM-07 | Emails come from the platform's sending address, with the supplier's email as Reply-To [DECISION D7]. | P0 |

### 7.7 Case Strength checklist

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-CHK-01 | Computed on read from case data. Never stored as a score, never phrased as a prediction. | P0 |
| FR-CHK-02 | Items (each `required` or `recommended`; status `met` / `missing` / `warning` / `not_applicable`; one-line action): | P0 |

| Item | Level | Met when | Action if not met |
| --- | --- | --- | --- |
| C01 Udyam number recorded | required | Profile has a valid Udyam number | "Add your Udyam number in Profile." |
| C02 Udyam proof | recommended | Certificate uploaded or provider-verified | "Upload your Udyam certificate." |
| C03 Eligible class | required | Class is micro or small | "Medium enterprises are not covered by ss.15–24." |
| C04 Activity eligibility | required (warning) | Activity is not trading | "Trading registrations may not be covered. Ask counsel." |
| C05 Registered before supply | required (warning) | Udyam registration date ≤ delivery date | "Registration after supply may limit your claim. Ask counsel." |
| C06 Invoice file | required | Evidence of type `invoice` exists | "Upload the invoice." |
| C07 Invoice details | required | Number, date, amount and buyer name present; buyer GSTIN present or marked unavailable | "Complete invoice details." |
| C08 Proof of delivery | required | `delivery_challan`, `delivery_photo` or `tracking_record` exists | "Upload the signed challan or a delivery photo." |
| C09 Proof of order | recommended | `purchase_order`, `written_terms`, `chat_export` or `email` exists | "Upload the order message or PO." |
| C10 Written terms evidence | required if deal = written | `written_terms` or `purchase_order` exists | "Upload the document showing agreed terms." |
| C11 Delivery intimation | recommended | An intimation is sent or recorded as manual | "Send the delivery intimation." |
| C12 No open objection | required | Acceptance state ≠ `objection_raised` | "Resolve the objection and record the removal date." |
| C13 Demand served | recommended (once overdue) | A demand is sent or recorded | "Send a demand letter." |
| C14 Buyer acknowledgement | recommended | Any acknowledgement response is recorded | "Save any message where the buyer confirmed receipt or the amount." |
| C15 Limitation window | required | Indicative limitation date is more than 180 days away | "Limitation may be close. Consult counsel now." |
| C16 Integrity | required | The last integrity check passed and nothing has changed since | "Run Verify integrity." |
| C17 No simulated data | required for filing | No simulated sends or sandbox verifications in the case | "Replace simulated items with real ones before filing." |

### 7.8 Buyer Cost Page

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-BCP-01 | Created only by explicit supplier action, as a share link of purpose `buyer_cost`. | P0 |
| FR-BCP-02 | Shows: supplier legal name and Udyam number; buyer name; invoice number, date and amount; acceptance date and basis; due date; days overdue; outstanding principal; illustrative interest to the as-of date (the view date); total. | P0 |
| FR-BCP-03 | Explains s.16 (interest), s.19 (75% pre-deposit to challenge an award) and s.43B(h) (deferred tax deduction) in plain language, each with "informational, not advice" wording. | P0 |
| FR-BCP-04 | Never shows evidence files, the timeline, the supplier's other cases or the supplier's bank details [DECISION D6]. | P0 |
| FR-BCP-05 | Default expiry 90 days [ASSUMPTION]; revocable; every view is logged (time, hashed IP, user agent). | P0 |
| FR-BCP-06 | Not indexable by search engines; no third-party scripts. | P0 |

### 7.9 Sealed Pack

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-PACK-01 | Generated on demand, versioned per case (v1, v2, …), immutable once created. | P0 |
| FR-PACK-02 | Contents (ZIP): `00_READ_ME_FIRST.pdf` (what this is, disclaimers, how to verify); `01_case_summary.pdf` (parties, invoice, dates with rule IDs, interest table); `02_timeline.pdf`; `03_evidence/` (non-excluded files, original bytes, prefixed by sequence and type); `04_communications/` (approved PDFs); `05_s63_certificate_DRAFT.pdf`; `06_questions_for_counsel.pdf`; `07_supplier_documents/` (supplier-level evidence such as the Udyam certificate, original bytes); `manifest.json` (every file's path, SHA-256 and size, timeline head hash, rule-set and rate-table versions, generation time, simulated flags). | P0 |
| FR-PACK-03 | The pack identifier is the SHA-256 of `manifest.json`, shown in the UI and the timeline. | P0 |
| FR-PACK-04 | Generation is blocked if the integrity check fails. Generation is allowed with warnings if checklist items are missing (they are listed in the pack). | P0 |
| FR-PACK-05 | The folder layout is "organised for ODR filing" but is **not** claimed to match the official portal list until that list is verified. | P0 |
| FR-PACK-06 | The s.63 certificate is clearly watermarked "DRAFT, for review by a qualified person", and pre-filled with device/system description, file list and hash values. | P0 |

### 7.10 Advocate sharing

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-ADV-01 | The supplier creates an advocate link for a specific pack version, entering the advocate's name (required) and email (optional). | P0 |
| FR-ADV-02 | Explicit consent text, versioned, must be accepted; consent is recorded. | P0 |
| FR-ADV-03 | Expiry 1–30 days, default 30; revocable; access logged (view, download). | P0 |
| FR-ADV-04 | No ranking, referral, directory or fee sharing with advocates. | P0 |

### 7.11 Dashboard

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-DASH-01 | "Needs attention" list: windows closing in ≤3 days, open objections, newly overdue cases, packs with failed integrity, limitation within 180 days. | P0 |
| FR-DASH-02 | Totals: outstanding principal, overdue principal, illustrative interest accrued (all open cases). | P0 |

## 8. Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| **Correctness** | Date and interest logic is pure, deterministic and covered by counsel-reviewable fixtures. It uses the Asia/Kolkata calendar for legal dates, Decimal arithmetic and integer paise. |
| **Integrity** | Evidence and timeline are append-only at the application and database level. Hash algorithm: SHA-256. Hashes are computed server-side only. |
| **Security** | OWASP ASVS Level 1 baseline; server-side authorisation on every request; secrets only in environment variables; tokens stored hashed. |
| **Privacy (DPDP Act 2023)** | Consent at sign-up; purpose-limited processing; data export and deletion request (P1); a retention policy [D12]; no third-party analytics or trackers in MVP. |
| **Performance** | On a mid-range Android phone over 4G: dashboard interactive within 3 s; delivery form submit acknowledged within 2 s (excluding upload); a 10 MB upload completes on a typical 4G connection; pack generation under 30 s for a 100 MB case. |
| **Reliability** | No background job is required for correctness (the clock is computed on read). An email failure never loses the approved communication. |
| **Availability** | MVP/demo: best effort on a single instance; daily backups. Production SLOs are Later. |
| **Accessibility** | WCAG 2.2 AA (see DESIGN.md). |
| **Browser support** | Latest two versions of Chrome (Android and desktop), Safari (iOS and macOS), Edge and Firefox. |
| **Localisation** | English UI in MVP; copy kept in one place so Hindi and other languages can be added later. INR shown in Indian digit grouping (Rs 5,00,000). Dates shown as DD MMM YYYY. |
| **Honesty** | Anything simulated or sandbox-derived is labelled everywhere it appears, including in PDFs and packs. |
| **Auditability** | Every state-changing case action produces a timeline event with an actor and a time. |

## 9. Pages and Screens

| # | Route | Screen | Access | Priority |
| --- | --- | --- | --- | --- |
| S1 | `/` | Landing: what PaySetu is and is not, sign-up and login links, disclaimer | Public | P0 |
| S2 | `/signup`, `/login` | Authentication | Public | P0 |
| S3 | `/forgot-password`, `/reset-password` | Password reset | Public | P1 |
| S4 | `/onboarding` | Business profile + eligibility summary + consent | Supplier | P0 |
| S5 | `/app` | Dashboard: needs attention, totals, recent cases | Supplier | P0 |
| S6 | `/app/cases` | Case list with filters and search | Supplier | P0 |
| S7 | `/app/cases/new` | New delivery (mobile-first quick capture) | Supplier | P0 |
| S8 | `/app/cases/[id]` | Case overview: DeemedClock day strip, key dates, amounts, next action | Supplier | P0 |
| S9 | `/app/cases/[id]/evidence` | Evidence Vault: list, upload, hashes, exclude, verify integrity | Supplier | P0 |
| S10 | `/app/cases/[id]/timeline` | Hash-chained timeline | Supplier | P0 |
| S11 | `/app/cases/[id]/responses` | Buyer responses: record, tag, resolve objection | Supplier | P0 |
| S12 | `/app/cases/[id]/payments` | Payments and interest calculation table | Supplier | P0 |
| S13 | `/app/cases/[id]/communications` | Intimation and demand drafts, approval, send | Supplier | P0 |
| S14 | `/app/cases/[id]/checklist` | Case Strength checklist | Supplier | P0 |
| S15 | `/app/cases/[id]/share` | Sealed Packs, advocate links, Buyer Cost links, access logs | Supplier | P0 |
| S16 | `/app/buyers`, `/app/buyers/[id]` | Buyer list and detail (with their cases) | Supplier | P0 |
| S17 | `/app/settings` | Profile, signatory, password, data export/deletion (P1), legal notices | Supplier | P0 |
| S18 | `/b/[token]` | Buyer Cost Page | Token holder | P0 |
| S19 | `/a/[token]` | Advocate read-only case view + pack download | Token holder | P0 |
| S20 | `/legal/terms`, `/legal/privacy`, `/legal/disclaimer` | Legal pages (content pending counsel) | Public | P0 |

## 10. Roles and Permissions

| Role | How identified | Description |
| --- | --- | --- |
| **Supplier owner** | Logged-in user | Owns one supplier profile and all its data |
| **Buyer viewer** | Bearer of a `buyer_cost` share token | External, read-only, one case's cost summary |
| **Advocate viewer** | Bearer of an `advocate` share token | External, read-only, one case's summary, timeline and one pack version |
| **Platform operator** | Server/CLI access only (no admin UI in MVP) | Maintains the RBI rate table and rule-set releases; no routine access to supplier evidence |

| Capability | Supplier owner | Buyer viewer | Advocate viewer | Operator |
| --- | --- | --- | --- | --- |
| Manage own profile, buyers, cases | Yes (own only) | No | No | No |
| Upload, exclude evidence | Yes | No | No | No |
| Approve and send communications | Yes (only actor allowed) | No | No | No |
| View cost summary | Yes | Yes (linked case) | Yes | No |
| View timeline and evidence list | Yes | No | Yes (linked case) | No |
| Download pack | Yes | No | Yes (linked pack version) | No |
| Run integrity verification | Yes | No | Yes (linked case) | No |
| Create or revoke share links, view access logs | Yes | No | No | No |
| Edit RBI rate table / rule set | No | No | No | Yes (via migration/CLI, with source and reviewer recorded) |

Supplier staff accounts and CA multi-client access are **Later** [D14].

## 11. Data Requirements

Logical entities. The physical schema is in DATABASE.md.

| Entity | Key data | Notes |
| --- | --- | --- |
| User | email, password hash, name, consent version and time | Personal data |
| Session | hashed token, expiry, revocation | |
| Supplier | legal and Udyam details, signatory, verification status | One per user (MVP) |
| Buyer | name, GSTIN, contact, email, phone | Personal data of contact persons |
| Case | invoice, delivery date, deal type, agreed terms, lifecycle | One invoice, one delivery |
| Buyer response | kind, received date, channel, summary, linked evidence, objection removal date | Drives the acceptance computation |
| Payment | amount, date, mode, reference, linked evidence | |
| Evidence item | type, original filename, size, MIME type, SHA-256, received time, exclusion | Files stored outside the DB |
| Timeline event | sequence, type, actor, payload, hashes | Append-only, hash-chained |
| Communication | kind, status, recipient, frozen content, content hash, send mode and result | |
| Share link | purpose, hashed token, recipient, expiry, revocation, consent | |
| Share access log | link, time, action, hashed IP, user agent | |
| Sealed pack | version, manifest hash, size, versions used, simulated flag | |
| Bank rate | effective-from date, rate, source, verifier | Reference data |

**Derived (never stored as truth):** acceptance state and dates, payment state, interest, checklist.

**Retention [DECISION D12]:** proposed default: case data is kept while the account is active and for 3 years after the indicative limitation date, or until deletion is requested and no legal hold applies.

**Sensitive data:** business identity data, buyer contact details, commercial documents (invoices may contain bank details), photographs (may contain location EXIF). No Aadhaar numbers are collected in MVP.

## 12. Integrations

| Integration | Purpose | MVP status | Notes |
| --- | --- | --- | --- |
| SMTP email (provider TBD) | Send approved intimations and demands; password reset | P0 (with `simulated` mode for demo) | [D7] Provider choice; SPF/DKIM must be set up for the sending domain |
| RBI bank rate | Interest rate history | P0 as a **manually maintained table** with source URLs | No live RBI API; the operator updates it when RBI changes the rate |
| Udyam / GSTIN verification (e.g. Cashfree Secure ID) | Verify supplier and buyer identity | P1, sandbox only; labelled "simulated" | Live behaviour unverified |
| DKIM verification (library, no external service) | Grade uploaded `.eml` files | P1 | DNS lookups needed at verification time |
| eSign / DSC (Leegality, Surepass, etc.) | Sign letters and certificates | Later | Signatory authority must be captured separately |
| WhatsApp Business API | Intake and sending | Later | |
| India Post tracking / postal evidence | Delivery of physical notices | Later | Real format unknown |
| RFC 3161 timestamp authority | Third-party time proof | Later | |
| MSME ODR portal | Filing | **None.** The supplier files manually | No public API known; document list unverified |

## 13. Loading, Empty and Error States

Visual treatment is in DESIGN.md. Required behaviour:

| Context | Loading | Empty | Error |
| --- | --- | --- | --- |
| Dashboard | Skeleton cards | "No deliveries yet. Log your first delivery." + primary button | "Could not load your dashboard." + Retry |
| Case list | Skeleton rows | No cases: same as dashboard. No filter results: "No cases match these filters." + Clear filters | Inline error + Retry |
| New delivery | Submit button shows progress; per-file upload progress bar | n/a | Field-level validation messages; a failed upload keeps the form data and offers Retry for that file only |
| Case overview | Skeleton day strip | n/a | 404 "Case not found or you don't have access" (same message for both) |
| Evidence | Per-file progress; hash appears when the server confirms | "No evidence yet. Start with the invoice and delivery proof." | Type/size rejection with the allowed list; a duplicate is reported as "Already in this case (uploaded [date])" |
| Integrity check | "Checking N files…" progress | n/a | Mismatch report listing each failed item (this is a result, not a system error) |
| Communications | Generating PDF… | "No letters yet." + "Prepare delivery intimation" | Send failure: "Not sent. [reason]. Your approved letter is saved." + Retry; and "Send it yourself" option |
| Checklist | Skeleton | n/a | Error + Retry |
| Pack generation | Step progress (verify → collect → render → seal) | "No packs yet." | Blocked by integrity failure with a link to the report; generic failure + Retry |
| Buyer Cost Page / Advocate page | Minimal skeleton | n/a | Expired: "This link has expired. Contact the supplier." Revoked: "This link is no longer active." Invalid: the same as revoked (no detail leaked) |
| Global | Top progress bar on route change | n/a | Offline banner: "You're offline. Changes will not be saved." Session expired → redirect to login with return path |

## 14. MVP Scope and Out of Scope

### In MVP (P0)

1. Email/password accounts and supplier profile with eligibility summary
2. Buyers
3. Case creation (one invoice, one delivery), including backdated entries
4. DeemedClock: computed acceptance states, dates and explanations under rule set `msmed-v1`
5. Buyer response recording (manual entry + evidence), objection removal
6. Interest calculator with a rate table, part payments and a calculation table
7. Evidence Vault: upload, SHA-256, append-only storage, exclusion, hash-chained timeline, integrity verification
8. Intimation and demand: templates, draft → approve → send (SMTP / simulated / manual), PDFs
9. Case Strength checklist (C01–C17)
10. Buyer Cost Page share links
11. Sealed Pack (versioned ZIP + manifest + draft s.63 certificate)
12. Advocate share links with consent, expiry, revocation and access log
13. Dashboard
14. Legal pages, disclaimers and simulated-data labelling

### P1 (only if time allows)

Password reset; `.eml` upload with DKIM; Udyam/GSTIN sandbox verification; data export and deletion request.

### Out of scope (Later or never)

| Item | Reason |
| --- | --- |
| eSign/DSC signing | Provider unverified; signatory-authority complexity |
| WhatsApp intake or sending | Optional in ideation; adds platform risk |
| Postal tracking parsing | Real format unknown |
| RFC 3161 timestamps | Not needed for MVP integrity claims |
| ODR portal integration / auto-filing | No API; PaySetu is not a filing agent |
| Multi-user organisations, CA multi-client | Not needed to validate the core problem |
| Payments, billing, subscriptions | Pricing not validated |
| Lawyer directory, referrals, ranking | Excluded on ethics grounds (Bar Council Rule 36) |
| Credit-bureau reporting, collection calls | Outside the product boundary |
| AI-based outcome prediction or legal advice | Excluded by design |
| Automatic AI tagging of buyer replies | Manual tagging is enough; avoids misclassification risk |
| Native mobile apps | A responsive web app covers gate capture |
| Hindi and regional languages | Later; copy is structured to allow it |
| Dark mode | Later [D9] |

## 15. Success Criteria

### Hackathon / demo readiness (must all pass)

1. The full Ravi journey (J2 → J8) runs end-to-end on a phone-sized screen in under 5 minutes, using a backdated delivery to show the deemed-acceptance state.
2. The interest fixture (Rs 5,00,000 at 17.25% for 12 months = Rs 93,406.72) and all rule fixtures pass.
3. Changing one byte of a stored evidence file makes integrity verification fail and name that file.
4. The Sealed Pack opens on Windows and macOS; the manifest hashes match the files.
5. Every simulated item is visibly labelled in the UI, PDFs and the manifest.
6. No communication can reach a buyer without an approval event in the timeline (tested).

### Pilot targets (to validate after MVP, [ASSUMPTION], to be approved)

| Metric | Target |
| --- | --- |
| Median time to log a delivery on a phone | ≤ 60 s |
| Suppliers who log ≥ 3 deliveries in the first 30 days | ≥ 50% of pilot suppliers |
| Cases with intimation sent within 2 days of delivery | ≥ 60% |
| Checklist "required" items complete at pack generation | ≥ 80% of packs |
| Advocate feedback: pack usable without re-collecting documents | ≥ 4 of 5 advocates surveyed |
| Integrity verification failures caused by system faults | 0 |

## 16. Decisions Requiring Approval

The live status, rationale, alternatives and the D → ADR/LR mapping are kept in [DECISIONS.md](DECISIONS.md). This table records the original proposal.

| ID | Decision | Proposed default | Why it matters |
| --- | --- | --- | --- |
| D1 | Hosting and region | Single small VM in an Indian region; see ARCHITECTURE.md | Cost, data location, simplicity |
| D2 | Sign-in method | Email + password (phone OTP Later) | OTP needs an SMS provider and DLT registration |
| D3 | Interest method | Monthly rests at rate/12 for full months; days/365 for the partial month; round to paisa at each rest | Matches the ideation chart; counsel must confirm |
| D4 | Part-payment allocation | Principal first (conservative) | Interest-first raises the claim; needs counsel |
| D5 | Which bank rate applies | Rate in force on the first day of each monthly period | The statute says "bank rate notified by RBI"; timing is ambiguous |
| D6 | Show supplier bank details on the Buyer Cost Page | No (contact details only) | Reduces phishing and fraud risk |
| D7 | Email provider and sender | Platform domain sender + supplier Reply-To; provider TBD | Deliverability; the sender identity reflects on the evidence |
| D8 | Product name | "PaySetu", subject to a trademark check | Earlier name was not checked either |
| D9 | Dark mode | Not in MVP | Scope |
| D10 | Rule set `msmed-v1` sign-off | Counsel review before any non-demo use | Legal correctness |
| D11 | Upload limit | 15 MB per file, 200 MB per case | Phone videos excluded; storage cost |
| D12 | Data retention | See Section 11 | DPDP compliance |
| D13 | Buyer Cost link default expiry | 90 days | Balance between usefulness and exposure |
| D14 | One user per supplier in MVP | Yes | Simplicity; staff roles Later |

## 17. Open Legal Questions for Counsel

1. Confirm that the tier S wording (R1–R9, R13) is current, with no later amendments, and confirm the tier I readings in Section 4.3, especially day counting (R4a) and "in writing" (R19). Each question is tracked as an LR item in [DECISIONS.md](DECISIONS.md).
2. Does a buyer acknowledgement within 15 days fix acceptance immediately, or does the window still run?
3. Interest method: monthly-rest mechanics, day-count basis, rate-change timing and payment allocation (D3–D5).
4. Effect of an objection received after Day 15, or one sent by a channel other than writing (e.g. a phone call).
5. Effect of Udyam registration dated after delivery (R10) and of trading registrations (R11).
6. Is the limitation computation in R12 correct for ODR/Council claims?
7. Review the delivery intimation and demand templates, and the draft s.63 certificate (Part A/B) against the BSA Schedule as published in the Gazette.
8. Whether the advocate-link design is consistent with Bar Council of India Rule 36.
9. Are the Buyer Cost Page statements on s.19 and s.43B(h) accurate, and what is the 43B(h) equivalent under the Income-tax Act 2025?
10. The official MSME ODR portal document list, needed to finalise the pack layout.
11. MSMED (Amendment) Act 2026: confirm the enacted text and S.O. 5575(E) (LR-21). Confirm supplier status under s.2(n) after the substituted s.8 (LR-23), the payment date when invoices settle through TReDS under new s.15A (LR-24), and the effect of the amended s.18, new s.18A and substituted s.19 once commenced (LR-25).
