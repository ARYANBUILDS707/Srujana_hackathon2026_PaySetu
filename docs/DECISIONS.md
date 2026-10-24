# PaySetu: Decision Register

| Field | Value |
| --- | --- |
| Status | v1.0, created during the documentation readiness review (25 Oct 2026) |
| Purpose | One place for every architecture/product decision (**ADR-xxx**) and every legal reading that needs counsel (**LR-xx**), with its status |
| Rule | Accepted entries here override the other documents (AGENTS.md Section 0). A status change is made in this file, in the same change as any affected document |

### Status vocabulary

| Status | Meaning | Can code depend on it? |
| --- | --- | --- |
| **Accepted** | Approved by the owner, or a direct owner instruction | Yes |
| **Proposed** | A safe engineering default written by the architect, awaiting owner confirmation. Chosen to be reversible | Yes, from the phase where it is needed, if the owner has not objected |
| **Open** | Needs an owner decision before the phase that depends on it | No. Ask |
| **Open: counsel** | A legal reading. The product ships a **labelled, configurable default** and never presents it as settled law | Only as a labelled default |
| **Counsel-confirmed** | Reviewed and confirmed by an advocate (name and date recorded) | Yes, and the label can be removed |
| **Superseded** | Replaced; kept for history | No |

---

## 1. Summary

### 1.1 Architecture and product decisions

| ID | Decision | Status | PRD ref | Needed by |
| --- | --- | --- | --- | --- |
| ADR-001 | Documentation layout: README + AGENTS at the root, everything else in `docs/` | Accepted | — | Done |
| ADR-002 | Product name "PaySetu" | Accepted (trademark check open) | D8 | Public launch |
| ADR-003 | Next.js + React + TypeScript + Tailwind frontend; Python + FastAPI backend | Accepted | — | Phase 0 |
| ADR-004 | Same-origin deployment behind one reverse proxy | Proposed | — | Phase 0 (dev proxy), Phase 12 |
| ADR-005 | SQLite (WAL) for MVP; PostgreSQL as the documented upgrade | Accepted | — | Phase 1 |
| ADR-006 | Legal state computed on read; no scheduler or queue | Proposed | — | Phase 2 |
| ADR-007 | Email + password sign-in with server-side sessions | Proposed | D2 | Phase 3 |
| ADR-008 | Append-only evidence, hash-chained timeline, DB triggers, content-addressed local storage | Proposed | — | Phase 1/4/5 |
| ADR-009 | Hosting: one small VM in an Indian region | Proposed | D1 | Phase 12 |
| ADR-010 | Email via an SMTP adapter + simulated mode; platform sender with supplier Reply-To; provider TBD | Proposed (provider Open) | D7 | Phase 9 |
| ADR-011 | Toolchain and versions | Proposed | — | **Phase 0 (M1)** |
| ADR-012 | Time and money representation | Proposed | A5 | Phase 2 |
| ADR-013 | Legal rules as a versioned TOML rule set with tiers and counsel flags | Proposed | — | **Phase 2 (M1)** |
| ADR-014 | Upload limits: 15 MB per file, 200 MB per case | Proposed | D11 | Phase 5 |
| ADR-015 | Buyer Cost Page: no bank details; link expiry 90 days | Proposed | D6, D13 | Phase 10 |
| ADR-016 | One user per supplier in MVP | Proposed | D14 | Phase 3 |
| ADR-017 | Light theme only in MVP | Proposed | D9 | Phase 7 |
| ADR-018 | Data retention and deletion policy | **Open** (owner + DPDP advice) | D12 | Before real users / Phase 13 |
| ADR-019 | No AI/LLM features in MVP | Proposed | — | — |
| ADR-020 | Git workflow and commit conventions | Proposed | — | **Phase 0 (M1)** |
| ADR-021 | Case granularity: one invoice, one delivery date | Proposed | A8 | Phase 2 |
| ADR-022 | Legal sign-off gate: no non-demo use until LR items are counsel-confirmed | **Open** (owner + counsel) | D10 | Before pilot |

### 1.2 Legal review register (all "Open: counsel")

| ID | Item | PRD ref | Product default (labelled) | Affects |
| --- | --- | --- | --- | --- |
| LR-01 | Day counting: "fifteen days from" excludes the delivery day; window ends Day 15; appointed day Day 16 | R4a | As stated | DeemedClock |
| LR-02 | No holiday or Sunday adjustment | R4b | No adjustment | DeemedClock |
| LR-03 | An objection after Day 15 does not move acceptance | R3a | Labelled "outside window" | DeemedClock |
| LR-04 | What counts as "in writing" (email, letter, chat yes; phone no; `other` counts as written) | R19, A6 | As stated | DeemedClock |
| LR-05 | Acknowledgement within the window does not end it early | R20 | Window still runs | DeemedClock |
| LR-06 | Multiple objections: acceptance = the last removal date | R21 | As stated | DeemedClock |
| LR-07 | Terms over 45 days are capped, not void | R6a | Cap with a note | DeemedClock |
| LR-08 | Udyam registration satisfies the s.2(n) memorandum | R9a | Treated as satisfying | Eligibility |
| LR-09 | Supplies before Udyam registration (*Silpi Industries*) | R10 | Warning only | Checklist |
| LR-10 | Trading-only Udyam registrations | R11 | Warning only | Checklist |
| LR-11 | Limitation: 3 years from interest start; warn at 180 days | R12, A7 | Indicative date | Checklist, UI |
| LR-12 | Interest mechanics: rate/12 per full month, days/365 for the partial month, half-up rounding at each rest | A1, A2 (D3) | As stated | Interest |
| LR-13 | Which bank rate applies (rate in force at the start of each monthly period) | A3 (D5) | As stated | Interest |
| LR-14 | Part-payment allocation (principal first) | A4 (D4) | As stated | Interest |
| LR-15 | s.43B(h) statement and its Income-tax Act 2025 equivalent | R14 | Informational text | Buyer Cost Page |
| LR-16 | BSA s.63 certificate form (Schedule Part A/B) | R15 | Watermarked DRAFT | Sealed Pack |
| LR-17 | Demand notice not mandatory; wording of the intimation and demand templates | R16 | Templates marked "pending review" | Communications |
| LR-18 | Advocate-link design vs Bar Council of India Rule 36 | — | No referral, ranking or fees | Sharing |
| LR-19 | Official ODR portal document list | FR-PACK-05 | "Organised for ODR filing" wording only | Sealed Pack |
| LR-20 | Currency of the tier S statute text (no amendments to ss.2(b), 15, 16, 19 since enactment) | R1–R9, R13 | Treated as current | All |

### 1.3 PRD decisions D1–D14: what actually blocks implementation

| PRD | Maps to | Blocks M1 (Phases 0 and 2)? | First phase blocked | Type |
| --- | --- | --- | --- | --- |
| D1 Hosting | ADR-009 | No | 12 | Engineering |
| D2 Sign-in | ADR-007 | No | 3 | Engineering |
| D3 Interest method | LR-12 | **Partly.** T2.3 needs agreement to build on labelled defaults, not a legal ruling | 2 (T2.3) | Legal |
| D4 Payment allocation | LR-14 | **Partly.** Same as D3 | 2 (T2.3) | Legal |
| D5 Rate timing | LR-13 | **Partly.** Same as D3 | 2 (T2.3) | Legal |
| D6 Bank details on the buyer page | ADR-015 | No | 10 | Product/risk |
| D7 Email provider | ADR-010 | No | 9 (simulated mode works without it) | Engineering |
| D8 Trademark | ADR-002 | No | Public launch | Business/legal |
| D9 Dark mode | ADR-017 | No | 7 | Product |
| D10 Rule-set sign-off | ADR-022 | No | Pilot / non-demo use | Legal gate |
| D11 Upload limits | ADR-014 | No | 5 | Engineering |
| D12 Retention | ADR-018 | No | Real users; Phase 13 deletion | Legal/DPDP |
| D13 Buyer link expiry | ADR-015 | No | 10 | Product |
| D14 Single user per supplier | ADR-016 | No | 3 (shapes the `suppliers` schema) | Product |

**Conclusion:** none of D1–D14 is a hard blocker for Phase 0. The only thing M1 needs is the owner's agreement that the Phase 2 interest engine may be built against the labelled defaults for LR-12 to LR-14, plus confirmation of ADR-011 (toolchain) and ADR-020 (Git workflow), which are new and not covered by D1–D14.

---

## 2. Architecture and Product Decisions (detail)

Each entry gives: **Decision**, **Rationale**, **Alternatives considered**, **Dependencies**, **Review requirement**.

### ADR-001: Documentation layout (Accepted, 25 Oct 2026)

- **Decision:** `README.md` and `AGENTS.md` at the repository root; PRD, DECISIONS, DESIGN, ARCHITECTURE, DATABASE, API and IMPLEMENTATION_PLAN in `docs/`.
- **Rationale:** the owner's instruction. Tools and coding agents look for README and AGENTS at the root.
- **Alternatives:** everything in `docs/` (the previous layout); everything at the root.
- **Dependencies:** AGENTS.md Section 0, ARCHITECTURE.md Section 6.
- **Review:** none.

### ADR-002: Product name "PaySetu" (Accepted; trademark check Open)

- **Decision:** the product is named PaySetu everywhere. "ProofFirst" appears only as the earlier working title.
- **Rationale:** the owner's instruction.
- **Alternatives:** ProofFirst (also unchecked).
- **Dependencies:** branding, domain name, email sender (ADR-010).
- **Review:** a trademark/name search before public launch (D8).

### ADR-003: Application stack (Accepted)

- **Decision:**
  - Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS.
  - Backend: Python + FastAPI.
  - PDFs: ReportLab. Tests: pytest + Playwright.
- **Rationale:** owner-specified; matches the ideation prototype's Python stack; strong typing on both sides through OpenAPI-generated types.
- **Alternatives:** Next.js full-stack only (it would lose the Python/ReportLab prototype path); Django (heavier).
- **Dependencies:** ADR-004, ADR-011.
- **Review:** none.

### ADR-004: Same-origin deployment (Proposed)

- **Decision:** one origin. The reverse proxy (Caddy) routes `/api/*` to FastAPI and everything else to Next.js. In development, Next.js rewrites `/api/*` to `localhost:8000`.
- **Rationale:** first-party cookies; no CORS; a minimal CSRF surface; simple HTTPS.
- **Alternatives:** separate API subdomain with CORS + bearer tokens (more attack surface and complexity); Next.js server-side proxying with cookie forwarding (more moving parts).
- **Dependencies:** ADR-007, ADR-009. `PUBLIC_BASE_URL` must be the browser origin.
- **Review:** owner confirmation.

### ADR-005: Database (Accepted)

- **Decision:** SQLite in WAL mode for the MVP, through SQLAlchemy 2.0 + Alembic. PostgreSQL (with RLS) is the documented upgrade path.
- **Rationale:** owner-specified for the prototype; zero operations; adequate for single-instance load.
- **Alternatives:** PostgreSQL from day one (more setup, no MVP benefit).
- **Dependencies:** DATABASE.md Sections 6 and 10.
- **Review:** revisit before multi-instance deployment.

### ADR-006: Legal state computed on read (Proposed)

- **Decision:** acceptance state, due dates, interest, payment state, checklist and next action are pure functions of stored facts plus "today". Nothing is scheduled; nothing derived is stored.
- **Rationale:** no cron or queue infrastructure; there is no stale status to reconcile; easy to test with a frozen clock; a rule change applies uniformly.
- **Alternatives:** a nightly job writing statuses (drift risk, extra infrastructure).
- **Dependencies:** ADR-013. Dashboard performance is fine at the expected MVP volumes (DATABASE.md Section 4).
- **Review:** revisit if p95 dashboard latency is over 300 ms.

### ADR-007: Authentication (Proposed; PRD D2)

- **Decision:**
  - Email + password, hashed with Argon2id.
  - Server-side sessions: a random token, stored hashed, in an `HttpOnly` / `Secure` / `SameSite=Lax` cookie. Idle expiry 7 days, absolute expiry 30 days.
  - CSRF protection via an Origin check plus a custom header.
- **Rationale:** needs no external provider; revocable sessions; simplest secure option.
- **Alternatives:**
  - Phone OTP: needs an SMS provider and DLT registration in India, and adds cost. It is the better UX for the target users, so it is a Later candidate.
  - Hosted auth SaaS: an extra dependency, and personal data goes to a third party.
  - JWTs: harder to revoke.
- **Dependencies:** ADR-004.
- **Review:** owner confirmation before Phase 3.

### ADR-008: Evidence integrity design (Proposed)

- **Decision:**
  - SHA-256 of the original bytes, computed server-side.
  - Write-once, content-addressed local storage.
  - An append-only, hash-chained timeline per case.
  - Database triggers that block UPDATE/DELETE except for the documented fields.
  - A verification routine that re-hashes files and re-walks the chain.
- **Rationale:** the product's core promise is tamper evidence. Enforcing it in the database guards against application bugs.
- **Alternatives:** an external timestamping authority (RFC 3161, Later); blockchain anchoring (rejected as unnecessary complexity); object storage with WORM (the future upgrade).
- **Dependencies:** DATABASE.md Sections 3.9–3.14 and 6.
- **Review:** counsel (LR-16) on how the hashes are described in the s.63 certificate. The product never claims that hashing alone makes evidence admissible.

### ADR-009: Hosting (Proposed; PRD D1)

- **Decision:** one small Linux VM in an Indian region. Caddy + systemd; nightly encrypted off-server backups.
- **Rationale:** the cheapest reliable option for a single-instance MVP; keeps data in India.
- **Alternatives:** PaaS (Render or Railway; region availability in India varies); containers on a managed service (more operational work).
- **Dependencies:** ADR-004, ADR-005.
- **Review:** the owner chooses the provider and account before Phase 12.

### ADR-010: Email delivery (Proposed; provider Open; PRD D7)

- **Decision:**
  - An `EmailSender` adapter with `smtp` and `simulated` implementations.
  - Sender: a platform domain address. Reply-To: the supplier's address.
  - No automatic retries. No tracking pixels.
- **Rationale:** demos work with no provider; there is no vendor SDK lock-in; it avoids double sends.
- **Alternatives:** sending from the supplier's own mailbox (OAuth complexity); a vendor HTTP API (lock-in, but better deliverability; any SMTP-capable provider works with the adapter).
- **Dependencies:** a sending domain with SPF/DKIM (depends on ADR-002 and a domain purchase).
- **Review:** the owner chooses a provider before real sends.

### ADR-011: Toolchain (Proposed; needed for M1)

- **Decision:**
  - Python 3.12 with `pip` + `venv` and pinned `requirements*.txt`.
  - Ruff and mypy (strict on `domain/`); pytest.
  - Node.js 20 LTS (22 LTS also acceptable) with `npm` and `package-lock.json`; ESLint, Prettier and `tsc --noEmit`; Playwright.
  - A root `Makefile` as the single command entry point.
- **Rationale:** the fewest extra tools; widely known; matches the AGENTS.md rules.
- **Alternatives:** `uv`/Poetry (faster, but an extra tool); pnpm (an extra tool); a task runner such as `just` (an extra tool).
- **Dependencies:** what is installed on the owner's machine (unknown).
- **Review:** owner confirmation before T0.2.

### ADR-012: Time and money representation (Proposed)

- **Decision:**
  - Legal dates are calendar dates in Asia/Kolkata.
  - Timestamps are UTC.
  - Money is an integer in paise in the DB, `Decimal` in the domain and a 2-decimal string in the API.
  - Rates are stored as basis points.
  - A single injectable clock.
- **Rationale:** removes floating-point and timezone defects in legal arithmetic.
- **Alternatives:** floats (rejected); storing local timestamps (ambiguous).
- **Dependencies:** PRD A5; DATABASE.md Section 1; API.md Section 1.1.
- **Review:** none.

### ADR-013: Rule-set format and legal tiers (Proposed; needed for M1)

- **Decision:**
  - Legal parameters and rule metadata live in versioned TOML (`msmed-v1.toml`), loaded into typed objects.
  - Each rule carries its tier (S, I or C), explanation text and a `counsel_confirmed` flag.
  - Outputs record the rule-set version, and they show a "pending legal review" label while any rule used is unconfirmed.
- **Rationale:** separates law from code, so counsel's answers change data, not architecture; it gives an audit trail of which rules produced which output; and it never silently settles an interpretation.
- **Alternatives:** Python constants (harder to review, easy to scatter); database tables (an admin UI would be needed, which is too much for MVP).
- **Dependencies:** PRD Section 4; LR-01 to LR-20.
- **Review:** owner confirmation before T2.1.

### ADR-014: Upload limits (Proposed; PRD D11)

- **Decision:** 15 MB per file and 200 MB per case. Types: PDF, JPEG, PNG, HEIC/HEIF, EML and UTF-8 text. Validated by magic bytes.
- **Rationale:** covers phone photos, scanned PDFs and email exports; excludes video; keeps the storage cost predictable.
- **Alternatives:** larger limits (cost, slower packs); allowing video (a large evidence-handling burden).
- **Dependencies:** ADR-008, ADR-009 (disk size).
- **Review:** owner confirmation before Phase 5.

### ADR-015: Buyer Cost Page content and link expiry (Proposed; PRD D6, D13)

- **Decision:** the page shows the supplier's contact details but **no bank details**. Buyer links expire after 90 days by default (configurable 1–90) and are revocable and logged.
- **Rationale:** payment details on a shareable link invite phishing and payment-diversion fraud. The supplier's invoice already carries the bank details.
- **Alternatives:** show bank details (convenient, but fraud risk); no expiry (exposure risk).
- **Dependencies:** API.md Section 2.13.
- **Review:** owner confirmation before Phase 10.

### ADR-016: One user per supplier (Proposed; PRD D14)

- **Decision:** `suppliers.owner_user_id` is unique. There are no staff or CA accounts in MVP.
- **Rationale:** a much simpler authorisation model. A later move to memberships is an additive migration.
- **Alternatives:** an organisations + memberships model now (premature).
- **Dependencies:** DATABASE.md Section 3.4.
- **Review:** owner confirmation before Phase 3.

### ADR-017: Light theme only (Proposed; PRD D9)

- **Decision:** the MVP ships light theme tokens only. The tokens are structured so a dark theme can be added later.
- **Rationale:** scope.
- **Review:** owner confirmation.

### ADR-018: Data retention and deletion (Open; PRD D12)

- **Proposed default:** keep case data while the account is active and for 3 years after the indicative limitation date. A deletion request disables the account immediately; an operator procedure removes the data unless a legal hold applies.
- **Why it is Open:** it depends on DPDP Act 2023 obligations and rules, on evidential needs and on business policy. It needs owner and legal input.
- **Alternatives:** delete immediately on request (risks destroying evidence the supplier still needs); retain indefinitely (DPDP risk).
- **Dependencies:** Phase 13 (T13.4), the privacy notice, the backup retention period.
- **Review:** owner + legal before any real user data is collected.

### ADR-019: No AI in MVP (Proposed)

- **Decision:** no LLM or ML features. Tagging buyer replies is manual. There is no outcome prediction.
- **Rationale:** determinism and auditability of legal outputs; avoids misclassification that would change legal dates.
- **Review:** a new PRD decision is required to add AI.

### ADR-020: Git workflow (Proposed; needed for M1)

- **Decision:**
  - `main` plus feature branches named `phase-<n>/<task>`.
  - Conventional Commits.
  - Commits and pushes only on the owner's request.
  - Remote hosting on GitHub (assumed; not needed for M1, which can be local).
- **Rationale:** matches AGENTS.md Section 13.
- **Alternatives:** trunk-only (less reviewable).
- **Review:** owner confirmation before T0.1.

### ADR-021: Case granularity (Proposed; PRD A8)

- **Decision:** one case = one invoice = one delivery date. Partial or multiple deliveries per invoice are out of scope.
- **Rationale:** each delivery has its own 15-day window; supporting several per invoice multiplies clock states and UI complexity.
- **Workaround:** log separate cases per delivery, each with its own invoice reference.
- **Review:** revisit after pilot feedback.

### ADR-022: Legal sign-off gate (Open; PRD D10)

- **Proposed default:** the app may be demoed with "pending legal review" labels. Any use with real suppliers requires every LR item that affects computed dates or amounts (LR-01 to LR-14, LR-20) to be Counsel-confirmed or explicitly accepted by the owner with a visible disclaimer.
- **Why it is Open:** the owner must decide the risk posture, and counsel must be engaged.
- **Review:** owner + advocate.

---

## 3. Legal Review Items (detail)

Each LR item has the same handling rules:

- **Status:** Open: counsel.
- **Product behaviour until confirmed:** the labelled default in Section 1.2, implemented as a configurable rule-set value (ADR-013).
- **What counsel needs to answer:** the question below.
- **When confirmed:** set the status to Counsel-confirmed, record the advocate's name and the date, set `counsel_confirmed = true` in the rule set, update `reviewed_by` in the fixtures, and bump the rule-set version if a value changes.

| ID | Question for counsel |
| --- | --- |
| LR-01 | Is "fifteen days from the day of delivery" counted excluding the delivery day (General Clauses Act s.9)? Is the verbal-deal due date Day 15 and the appointed day Day 16? |
| LR-02 | Should any date roll forward when it falls on a Sunday or public holiday? |
| LR-03 | Is a written objection received after Day 15 legally irrelevant to the day of acceptance? |
| LR-04 | Do email, WhatsApp/SMS and other electronic messages count as an objection "in writing"? Should an unspecified channel be treated as written? |
| LR-05 | Does an express acknowledgement within 15 days fix acceptance immediately, or does the window still run? |
| LR-06 | With several objections, is the day of acceptance the day the last one is removed? What if an objection covers only part of the goods? |
| LR-07 | If written terms exceed 45 days, is the effect a cap at 45 days, or does the "no agreement" (Day 15) rule apply? |
| LR-08 | Does Udyam registration satisfy "filed a memorandum" in s.2(n) for all supplies after July 2020? |
| LR-09 | Current position on supplies made before the supplier's Udyam registration (*Silpi Industries* and later cases)? |
| LR-10 | Are trading-only Udyam registrants excluded from Chapter V protections? |
| LR-11 | What is the correct limitation start and period for Council/ODR claims, and for which forum? |
| LR-12 | Interest mechanics under "compound interest with monthly rests": rate/12 per month or days/365, partial-month treatment, rounding |
| LR-13 | Which bank rate applies when RBI changes the rate during the delay period? |
| LR-14 | Should part payments go to interest first or principal first? |
| LR-15 | Is the s.43B(h) explanation accurate, and what is the corresponding provision under the Income-tax Act 2025? |
| LR-16 | Is the draft s.63 certificate (Part A by the party, Part B by an expert) correct against the BSA Schedule as published in the Gazette? Who should sign it? |
| LR-17 | Approve the wording of the delivery intimation and demand templates. Confirm that a demand notice is not a precondition |
| LR-18 | Is a supplier-chosen, fee-free advocate share link consistent with Bar Council of India Rule 36? |
| LR-19 | What documents and format does the official MSME ODR portal require? |
| LR-20 | Have ss.2(b), 2(n), 15, 16 or 19 been amended since 2006? (Tier S wording was checked only against the PRS India copy of the Act as enacted) |

**Tier S verification record:** on 25 Oct 2026 the wording of ss.2(b) (including the Explanation), 2(n), 15, 16, 17 and 19 was compared against the PRS India copy of the MSMED Act 2006 as enacted. It matched what PRD Section 4.2 encodes. It was not compared with the India Code consolidation or any amendment acts (see LR-20).

---

## 4. Readiness Review Log (25 Oct 2026)

Contradictions found during the documentation review, and their resolutions:

| # | Finding | Resolution | Files |
| --- | --- | --- | --- |
| 1 | README and AGENTS were in `docs/`; the owner wants them at the root | Moved; links and paths updated | README.md, AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md |
| 2 | Legal rules mixed statute text, interpretation and product assumptions under one "[COUNSEL]" label | PRD Section 4 split into tiers S, I and C; statute wording checked; LR register created | PRD.md, DECISIONS.md |
| 3 | `communications.buyer_share_link_id` referenced `share_links`, which is created in a later migration and phase | Column added in migration 7 / task T10.8; demand letters in Phase 9 ship without the link | DATABASE.md, API.md, IMPLEMENTATION_PLAN.md |
| 4 | Supplier-level evidence (Udyam certificate) had no case, but every evidence add was meant to write a case timeline event | No timeline event for supplier-level evidence; partial unique index; included in packs under `07_supplier_documents/` | DATABASE.md, PRD.md, API.md, IMPLEMENTATION_PLAN.md |
| 5 | `verification_result` was a timeline event type, but verification is supplier-level | Removed from timeline event types | DATABASE.md |
| 6 | API `POST /payments/{id}/void` takes a reason, but there was no column for it | `payments.void_reason` added | DATABASE.md |
| 7 | API `record-manual` takes a `sent_on` date, but the DB only had the `sent_at` timestamp | `communications.manual_sent_on` added | DATABASE.md, API.md |
| 8 | The PRD communication lifecycle omitted the `sending` state used by the DB and API | Added as transient | PRD.md |
| 9 | Phase 4 computes the checklist and dashboard before evidence, responses, payments and communications tables exist | Empty inputs until each later phase; no early placeholder tables | IMPLEMENTATION_PLAN.md |
| 10 | The CSRF origin check would fail in development, because `PUBLIC_BASE_URL` was ambiguous between the API and web ports | Defined as the browser-facing origin (`http://localhost:3000` in development) | ARCHITECTURE.md |
| 11 | The README roadmap phases did not match the implementation plan's phases | README now mirrors Phases 0–13 | README.md |
| 12 | The README said "ss.15 to 25", but the delayed-payment chapter is ss.15–24 | Corrected | README.md |
| 13 | There was no explicit mapping from the five PRD modules to code | Module → code table added | ARCHITECTURE.md Section 3.3 |
| 14 | Unclear treatment of the `other` response channel, multiple objections and holidays | Tier I/C rules R19, R21, R4b, A6 + LR-02/04/06 | PRD.md, DATABASE.md |
| 15 | README delivery-capture target (20 s) conflicted with the PRD requirement (≤ 60 s) | README states both (requirement vs aspiration) | README.md |

Checks that passed with no change needed:

- Project name: PaySetu is used throughout; ProofFirst appears only as the earlier title.
- The five module names match across README, PRD, DESIGN and ARCHITECTURE.
- Every API endpoint maps to existing tables or computed values.
- The stack in ARCHITECTURE matches the owner-proposed stack.
- The rate-limit tables in ARCHITECTURE and API agree.
