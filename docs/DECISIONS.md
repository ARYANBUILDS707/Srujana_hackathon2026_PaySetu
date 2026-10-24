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
| **Provisional default** | An "Open: counsel" item whose default the owner has approved for simulation and development. It is **not** a validated legal rule, and every output that uses it stays labelled "pending legal review" | Yes, as a labelled default |
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
| ADR-011 | Toolchain and versions (Python 3.12, Node 22 LTS) | Accepted (25 Oct 2026) | — | Phase 0 (done) |
| ADR-012 | Time and money representation | Proposed | A5 | Phase 2 |
| ADR-013 | Legal rules as a versioned TOML rule set with tiers and counsel flags | Proposed | — | **Phase 2 (M1)** |
| ADR-014 | Upload limits: 15 MB per file, 200 MB per case | Proposed | D11 | Phase 5 |
| ADR-015 | Buyer Cost Page: no bank details; link expiry 90 days | Proposed | D6, D13 | Phase 10 |
| ADR-016 | One user per supplier in MVP | Proposed | D14 | Phase 3 |
| ADR-017 | Light theme only in MVP | Proposed | D9 | Phase 7 |
| ADR-018 | Data retention and deletion policy | **Open** (owner + DPDP advice) | D12 | Before real users / Phase 13 |
| ADR-019 | No AI/LLM features in MVP | Proposed | — | — |
| ADR-020 | Git workflow and commit conventions | Accepted (25 Oct 2026) | — | Phase 0 (done) |
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
| LR-12 | Interest mechanics: rate/12 per full month, days/365 for partial or split periods, half-up rounding at each rest, accrual through the as-of date inclusive | A1, A2, A10 (D3) | **Provisional default** (owner-approved 25 Oct 2026) | Interest |
| LR-13 | Which bank rate applies (rate in force at the start of each monthly period) | A3 (D5) | **Provisional default** (owner-approved 25 Oct 2026) | Interest |
| LR-14 | Part-payment allocation (principal first) | A4 (D4) | **Provisional default** (owner-approved 25 Oct 2026) | Interest |
| LR-15 | s.43B(h) statement and its Income-tax Act 2025 equivalent | R14 | Informational text | Buyer Cost Page |
| LR-16 | BSA s.63 certificate form (Schedule Part A/B) | R15 | Watermarked DRAFT | Sealed Pack |
| LR-17 | Demand notice not mandatory; wording of the intimation and demand templates | R16 | Templates marked "pending review" | Communications |
| LR-18 | Advocate-link design vs Bar Council of India Rule 36 | — | No referral, ranking or fees | Sharing |
| LR-19 | Official ODR portal document list | FR-PACK-05 | "Organised for ODR filing" wording only | Sealed Pack |
| LR-20 | Currency of the tier S statute text (no amendments to ss.2(b), 15, 16, 19 since enactment) | R1–R9, R13 | Treated as current | All |
| LR-21 | **MSMED (Amendment) Act 2026 (Act 16 of 2026):** confirm the enacted text and S.O. 5575(E) commencement. Bill text and the PIB summary show **no amendment** to ss.2(b), 15, 16 or 17 (see Section 3) | All R rules | No formula change; `msmed-v1` unchanged; every output still lists LR-21 as pending | All |
| LR-22 | Agreed payment days (written deal) are counted from the day of acceptance | A9 | As stated | DeemedClock |
| LR-23 | s.2(n) "supplier" after the substituted s.8 (voluntary registration on a national platform) | R9, R9a | Eligibility still requires a Udyam number | Eligibility |
| LR-24 | Payment date for s.15/s.16 when invoices settle through TReDS under new s.15A | R5–R8 | Payment = date the supplier receives funds (as entered) | Interest |
| LR-25 | Amended s.18, new s.18A and substituted s.19 (not commenced): future buyer-facing and forum text | R13 | Current s.19 wording only | Buyer Cost Page |

### 1.3 PRD decisions D1–D14: what actually blocks implementation

| PRD | Maps to | Blocks M1 (Phases 0 and 2)? | First phase blocked | Type |
| --- | --- | --- | --- | --- |
| D1 Hosting | ADR-009 | No | 12 | Engineering |
| D2 Sign-in | ADR-007 | No | 3 | Engineering |
| D3 Interest method | LR-12 | No longer blocking. The owner approved the default as a **provisional simulation default** (25 Oct 2026); legal review remains open | — | Legal |
| D4 Payment allocation | LR-14 | No longer blocking. Same as D3 | — | Legal |
| D5 Rate timing | LR-13 | No longer blocking. Same as D3 | — | Legal |
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

### ADR-011: Toolchain (Accepted, 25 Oct 2026)

*Accepted on the basis of the approved Phase 0 workflow. Node.js 22 LTS (tested 22.23.4) is the supported version, pinned by `.nvmrc`. `package.json` `engines` also allows Node 20.9+. Python 3.12 (tested 3.12.13).*

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
- **Dependencies:** PRD Section 4; LR-01 to LR-25.
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

### ADR-020: Git workflow (Accepted, 25 Oct 2026)

*Accepted on the basis of the approved Phase 0 workflow (work on `dev`; the owner commits and pushes).*

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

- **Proposed default:** the app may be demoed with "pending legal review" labels. Any use with real suppliers requires every LR item that affects computed dates or amounts (LR-01 to LR-14, LR-20 to LR-24) to be Counsel-confirmed or explicitly accepted by the owner with a visible disclaimer.
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
| LR-21 | Confirm the text and status of the MSMED (Amendment) Act 2026: whether it is enacted, its Gazette citation and its commencement notification(s). Then confirm, provision by provision, what changes for ss.15–19 (including the reported new s.15A and s.18(3A)), and which version governs a supply delivered before, on or after commencement. Also confirm the reported Income-tax Act 2025 s.37(2)(g) equivalent of s.43B(h) (links to LR-15) |
| LR-22 | For a written deal stated as "N days", are the days counted from the day of acceptance, the delivery date or the invoice date? |
| LR-23 | After the substitution of s.8 (Amendment Act 2026 s.5: free, voluntary filing on a national digital platform), does an enterprise still need a filed memorandum to be a "supplier" under the unamended s.2(n)? Do existing Udyam registrations satisfy it (Amd s.17 savings)? What is the position of an unregistered micro or small enterprise? |
| LR-24 | For buyers bound by new s.15A (CPSEs and notified entities settling through TReDS): which date counts as payment for s.15 and s.16 (invoice acceptance on TReDS, financier payout to the supplier, or buyer settlement)? Does TReDS discounting affect the supplier's claim to s.16 interest? |
| LR-25 | When Amendment Act ss.8–10 commence (amended s.18, new s.18A, substituted s.19), what must change in buyer-facing and forum text: the 90-day mediation and award timelines, jurisdiction by the supplier's registered address, recovery as arrears of land revenue, and the 6-month / 50% payout rule? Which version applies to references and awards already pending? |

**LR-21 verification record (updated 25 Oct 2026, M1 close).**

What was checked, and how reliable each source is:

| Item | Finding | Source | Reliability |
| --- | --- | --- | --- |
| Bill text | Read in full: 17 clauses (Bill No. LXXII of 2026, as introduced in Rajya Sabha on 28 Jul 2026) | PRS India copy of the Bill PDF | Official Bill text, **as introduced** |
| Passage | Passed by Rajya Sabha 3 Aug 2026 and Lok Sabha 7 Aug 2026. Whether amendments were made during passage is not stated | PRS Bill Track; PIB factsheet of 11 Aug 2026 ("passed by the Parliament in August 2026") | Official / semi-official. The PIB factsheet's comparison table matches the introduced text on every point below |
| Act No. 16 of 2026; assent and Gazette publication on 13 Aug 2026 | Reported | SCC Online, IMPRI | **Secondary. Not seen in the Gazette** |
| Notification S.O. 5575(E) of 12 Oct 2026 (F. No. 2/1(1)/2022-P&G/Policy/E) | Reported to bring Amendment Act ss.2–7, 11 and 13–17 into force on 15 Oct 2026, and s.12 on 15 Dec 2026. Amendment Act ss.8–10 have **no** appointed date | TaxGuru; masllp.com | **Secondary. The Gazette copy could not be retrieved; egazette.gov.in results were not indexed** |
| Enacted (as-passed) text | Not obtained | — | **Gap** |

**Comparison with PaySetu rules.** Section numbers are MSMED Act sections. "Amd s.N" means a section of the Amendment Act.

| MSMED provision | Amendment | Commenced? (secondary) | Effect on PaySetu |
| --- | --- | --- | --- |
| s.2(b) day of acceptance, deemed acceptance, appointed day (R1–R4) | **Not amended.** Amd s.2 only inserts cl.(da) "Development Commissioner" and edits cl.(g), (h), (j), (m) | — | None. DeemedClock unchanged |
| s.15 payment, 45-day cap (R5, R6) | **Not amended**; a new s.15A is inserted after it | — | None. Formulas unchanged |
| s.16 compound interest, monthly rests, 3× bank rate (R7, R8) | **Not amended** | — | None. Interest engine unchanged |
| s.17 recovery | **Not amended** | — | None |
| s.2(n) "supplier" (R9) | Text **not amended**, but it still refers to the authority in s.8(1), and **s.8 is substituted** (Amd s.5): free, *voluntary* filing on a national digital platform | Yes, 15 Oct 2026 | Eligibility still requires a Udyam number (conservative). New question **LR-23** |
| s.7 classification | s.7(1) substituted: classification by notification, on investment **and** turnover | Yes | None in code (class comes from the Udyam record). The README's threshold table must be re-checked against current notifications |
| **s.15A (new)**: CPSEs, and entities the Centre or States notify, must route invoice settlement through an RBI-authorised TReDS platform | Inserted (Amd s.7) | Yes | No formula change. New question **LR-24** on how TReDS settlement interacts with s.15/s.16 payment dates. Possible future product field ("buyer is a CPSE / notified entity") needs a PRD decision |
| s.18 mediation and arbitration: 90-day mediation (3A), 30-day reference to arbitration (4), 90-day award (4A), jurisdiction by the supplier's registered address (5), online mechanism (6), (7) | Amended (Amd s.8) | **No** | None now. Affects forum and timeline copy later (Phase 9/10). **LR-25** |
| s.18A (new): settlements and awards recoverable as arrears of land revenue; a debt under the IBC | Inserted (Amd s.9) | **No** | None now. **LR-25** |
| s.19 setting aside (R13) | Substituted (Amd s.10): adds mediated settlements, a "mandatory" 75% deposit, at least 50% paid to the supplier after 6 months pending, and jurisdiction at the supplier's address | **No** | R13 (the current s.19) stays in force. Buyer Cost Page s.19 text must not use the new wording until commenced. **LR-25** |
| ss.20, 21 Facilitation Councils | Substituted (Amd s.11, s.12) | s.20 yes; s.21 from 15 Dec 2026 | None |
| s.22A (new): CPSE TReDS disclosure | Inserted (Amd s.13) | Yes | None |
| s.27 penalties (incl. buyer's non-disclosure under s.22) | Substituted with graded penalties; s.27A adjudication (Amd s.14) | Yes | Informational only |
| Amd s.17 savings | Prior actions and notifications continue | Yes | Supports treating existing Udyam registrations as continuing (still LR-23) |
| s.43B(h) / Income-tax Act 2025 | Not part of this Act | — | LR-15 unchanged |

**Conclusion.** There is no statutory basis to change any DeemedClock or interest rule; `msmed-v1` stays as it is. Because ss.2(b), 15 and 16 are not amended, the version question in LR-21 (old vs new text for supplies before or after commencement) does not change any computed date or amount. Counsel should still confirm this against the enacted text. LR-21 remains **Open: counsel** until the Gazette copies of Act 16 of 2026 and S.O. 5575(E) are checked.

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

---

## 5. Milestone M1-B Log (25 Oct 2026)

Decisions recorded at the start of M1-B (T2.1–T2.7):

- ADR-011 and ADR-020 accepted, based on the approved Phase 0 workflow. Node.js 22 LTS stays the supported version.
- D3–D5 (LR-12, LR-13, LR-14) recorded as **provisional simulation defaults**: owner-approved for development, not validated legal rules. Outputs stay labelled "pending legal review".
- LR-21 (MSMED (Amendment) Act 2026) and LR-22 (base date for "N days" written terms) added. All earlier advocate-review items remain open.

Conflicts and gaps found while implementing, and how each was resolved:

| # | Finding | Resolution | Files |
| --- | --- | --- | --- |
| 1 | IMPLEMENTATION_PLAN T2.1 put the TOML loader in `app/domain/rules.py`, but AGENTS.md forbids I/O in `domain/` | Pure validation stays in `domain/rules.py`; file reading lives in `app/rules/loader.py` | ARCHITECTURE.md 3.2, IMPLEMENTATION_PLAN.md T2.1 |
| 2 | The PRD did not say what "N days" in written terms counts from | Counted from acceptance (A9); question raised as LR-22 | PRD.md 4.4 |
| 3 | The PRD did not say whether interest accrual includes the as-of day, or how a mid-month payment affects a monthly rest | A10: accrual through the as-of date inclusive; a payment splits the month into days/365 segments (part of D3 / LR-12) | PRD.md 4.4 |
| 4 | The limitation date from 29 Feb was undefined | A11: falls back to 28 Feb (conservative) | PRD.md 4.4 |
| 5 | The plan's reference figure was "Rs 93,407 ± Re 1" | Tested exactly: Rs 93,406.72 (arithmetic regression, not statutory proof) | IMPLEMENTATION_PLAN.md, AGENTS.md, PRD.md |
| 6 | The plan requires 100% **branch** coverage on `domain/`, but no coverage tool was approved | **Resolved at M1 close:** the owner approved pytest-cov. Measured 100% line and 100% branch coverage on `app/domain` (1,023 statements, 264 branches), now enforced by `make test` | Makefile, `backend/pyproject.toml` |
| 7 | MSMED Act commencement date (2 Oct 2006) used as the rule-set `effective_from` comes from secondary knowledge | Recorded in the rule-set `legal_basis` as "to be verified (LR-20)" | `msmed-v1.toml` |

---

## 6. Milestone M1 Close Log (25 Oct 2026)

| Item | Result |
| --- | --- |
| Branch coverage (owner-approved `pytest-cov==7.1.0`, `coverage==7.17.0`) | `app/domain`: 1,023 statements, 0 missed; 264 branches, 0 partial; **100% line and branch**. The existing tests already covered every branch, so no new coverage-only tests were needed. No exclusions or `pragma` markers. Gate: `[tool.coverage.report] fail_under = 100`, run by `make test`; confirmed to fail on a partial run (8.94%) |
| MSMED (Amendment) Act 2026 review (LR-21) | Bill text read in full. The PIB summary of the passed Bill matches it. **ss.2(b), 15, 16 and 17 are not amended**, so no DeemedClock or interest change (no statutory basis). Act No. 16 of 2026 and S.O. 5575(E) (12 Oct 2026) confirmed only from secondary sources; Gazette copies not retrieved. New questions LR-23 (s.2(n) vs substituted s.8), LR-24 (TReDS payment date under s.15A) and LR-25 (s.18/18A/19 once commenced) |
| Rule-set metadata | `msmed-v1` `legal_basis`, `pending_reviews` (+LR-23, LR-24) and `decision_refs` for R8, R9 and R13 updated. **No parameter or formula changed** (a test asserts the 15/15/45/3× values) |
| Tests | 208 passed (previously 207: one test strengthened for the amendment flags, one added to pin the statutory periods) |

---

## 7. Hackathon Demo Vertical Slice (25 Oct 2026, owner-directed)

The owner prioritised an evaluation-ready backend slice over strict phase order. Deviations, all deliberate and to be resolved in the listed phase:

| Deviation | Why | Resolve in |
| --- | --- | --- |
| **No authentication.** One synthetic demo supplier (`make seed`); demo routes are mounted only when `APP_ENV` is not `production` and responses carry `"demo_mode": true` | Auth (Phase 3) was out of time scope | Phase 3: replace demo-supplier resolution with `SupplierPrincipal`; remove `is_demo` routing |
| **Schema subset** in one migration (`7f9909eb7e4c`): suppliers (no `owner_user_id`, plus `is_demo`), buyers, cases, buyer_responses, evidence_items, timeline_events (append-only triggers), bank_rates (`verified` flag, nullable `verified_by`) | Minimum tables for the demo | Phase 3 adds users/sessions and `owner_user_id`; later migrations add payments, communications, packs, share links |
| **Evidence store pulled forward** from T1.6 (`app/storage/evidence_store.py`): write-once, content-addressed, magic-byte allow-list, 0600 files | Needed for uploads | T1.6 reviews it against its criteria |
| **Bank rate is unverified.** The seed inserts only 5.75% from 2026-10-07 (LS-03 ideation document), `verified = false`; no earlier rate is invented. Interest periods it does not cover report `rate_data_unavailable` | No verified RBI series on record | Before real use: load verified RBI rates (operator migration, DATABASE.md 3.15) |
| **Letters not built**: intimation and demand are reported as not done (checklist C11, C13) | Out of scope | Phase 9 |
| Evidence uploads rate-limited under one demo key | No users yet | Phase 3/5 (per-user key) |
