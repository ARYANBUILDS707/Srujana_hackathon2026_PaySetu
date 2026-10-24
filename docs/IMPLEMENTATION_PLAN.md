# PaySetu: Implementation Plan

| Field | Value |
| --- | --- |
| Status | Draft v1.1 (consistency review), derived from PRD, DECISIONS, DESIGN, ARCHITECTURE, DATABASE, API and AGENTS |
| Scope | MVP (P0) in Phases 0–12; P1 items in Phase 13 |
| Rule | Build foundations before dependent features. Each task is small enough to implement, test and review on its own. Follow the root `AGENTS.md` for every task, and check `docs/DECISIONS.md` for the status of any decision a task depends on |

---

## How to use this plan

- Tasks are numbered `T<phase>.<n>`. Implement them **in order** unless a task says it can run in parallel.
- Each task is one branch (`phase-<n>/<short-task>`) and one review.
- A task is done only when it meets the Definition of Done in AGENTS.md Section 14 **and** its completion criteria here.
- The "Prompt" column maps each phase to the reusable prompt to run it with (the owner's prompt set: 8 Setup, 9 Feature, 10 Database & Backend, 11 Auth, 13 Integration, 14 QA, 15 Debug, 16 Security, 17 Review, 18 Deploy, 19 Monitoring, 20 Final audit).

### Pre-conditions (owner, before or during Phase 0)

| Item | Needed by | Status |
| --- | --- | --- |
| Approve the proposed engineering defaults needed by Milestone M1: ADR-011 (toolchain), ADR-013 (rule-set format), ADR-020 (Git workflow) | Phase 0 / Phase 2 | Proposed, see DECISIONS.md |
| Agree that Phase 2 may build the interest engine with **labelled, configurable defaults** for LR-12, LR-13 and LR-14 (D3–D5) while counsel review is pending | Phase 2 (T2.3) | Open, see DECISIONS.md |
| Approve the remaining engineering defaults before their phase: ADR-007 (D2) before Phase 3, ADR-014 (D11) before Phase 5, ADR-010 (D7) before Phase 9, ADR-015 (D6, D13) before Phase 10, ADR-009 (D1) before Phase 12 | Per phase | Proposed |
| Install Python 3.12, Node.js 20 LTS (or 22 LTS), Git | Phase 0 | Unknown |
| Initialise the Git repository (the folder is not a repo yet) | Phase 0 | Open |
| Book an advocate review of the legal register (LR-01 … LR-25), templates and the s.63 draft | Before any non-demo use | Open |
| SMTP account (or stay `simulated` for demo) | Phase 9 | Open |

### Phase overview

| Phase | Name | Depends on | Prompt |
| --- | --- | --- | --- |
| 0 | Repository and tooling setup | — | 8 |
| 1 | Backend foundation | 0 | 10 |
| 2 | Legal and integrity domain core (pure logic) | 0 (can run in parallel with 1) | 9 |
| 3 | Authentication and supplier profile | 1 | 11 |
| 4 | Buyers, cases and timeline | 2, 3 | 10 / 9 |
| 5 | Evidence Vault | 4 | 9 |
| 6 | Responses, payments, clock and interest API | 4, 5 | 9 |
| 7 | Frontend foundation and design system | 0; API from 3 | 8 / 9 |
| 8 | Frontend core case flows | 6, 7 | 9 |
| 9 | Communications (intimation and demand) | 6, 8 | 9 / 13 |
| 10 | Sealed Pack, share links and public pages | 9 | 9 |
| 11 | Demo readiness, QA and hardening | 10 | 14, 16, 17 |
| 12 | Deployment, monitoring and final audit | 11 | 18, 19, 20 |
| 13 | P1 enhancements | 12 (or after 11 if time allows) | 9 / 13 |

---

## Phase 0: Repository and Tooling Setup

**Goal:** an empty but runnable monorepo that matches ARCHITECTURE.md Section 6, with lint, typecheck and test commands working on both sides. No product features.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T0.1 | Initialise the Git repository, `.gitignore` (`storage/`, `.env`, `node_modules`, `.venv`, `*.db`, build output), root `Makefile` with targets `dev`, `lint`, `typecheck`, `test`, `e2e`, `migrate`, `seed` (targets may be stubs that print "not yet available") | `.gitignore`, `Makefile` | `git status` clean after the first commit; `make help` lists targets |
| T0.2 | Backend skeleton: venv, pinned `requirements.txt` / `requirements-dev.txt` (approved list only), `pyproject.toml` (ruff, mypy, pytest config), `app/main.py` app factory with `GET /api/v1/health` returning static `ok`, `backend/.env.example` | `backend/**` | `uvicorn` starts; `curl /api/v1/health` returns 200; `ruff`, `mypy`, `pytest` (one smoke test) pass |
| T0.3 | Frontend skeleton: Next.js App Router + TypeScript strict + Tailwind + ESLint + Prettier; dev rewrite `/api/*` → `API_ORIGIN`; `frontend/.env.example`; a placeholder `/` page | `frontend/**` | `npm run dev` serves `/`; `npm run lint`, `npm run typecheck` (`tsc --noEmit`) and `npm run build` pass; `/api/v1/health` reachable through the dev proxy |
| T0.4 | Playwright installed with one smoke test (home page loads at 360×800 and 1280×800) | `frontend/tests/e2e/`, `playwright.config.ts` | `make e2e` passes locally |
| T0.5 | Update the root `README.md` sections "Installation" and "Current Implementation Status" with the commands verified in T0.2–T0.4 | `README.md` | Commands in the README were actually run |

- **Dependencies:** owner pre-conditions (tools, Git).
- **DB/API changes:** health endpoint only.
- **Tests:** backend smoke test; Playwright smoke test.

---

## Phase 1: Backend Foundation

**Goal:** configuration, database, migrations, errors, logging, security middleware and time handling, all in place before any feature.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T1.1 | Typed settings via `pydantic-settings` (all variables in ARCHITECTURE.md Section 12); startup validation; production gate for simulated adapters | `app/config.py` | Missing required variables fail startup with a clear message; tests cover the gate |
| T1.2 | DB engine + session + SQLite pragmas (WAL, foreign_keys, busy_timeout); Alembic configured; test fixture that builds a temp DB with `alembic upgrade head` | `app/db.py`, `alembic/`, `tests/conftest.py` | Empty migration runs; pragma test passes |
| T1.3 | Error framework: typed exceptions → `application/problem+json` handler; `request_id` middleware; structured JSON logging with redaction | `app/errors.py`, `app/main.py`, `app/logging.py` | Tests: each error type maps to the documented status and code; logs contain no bodies or tokens |
| T1.4 | Injectable `Clock` provider (UTC now + Asia/Kolkata today) and a test-freezing fixture | `app/clock.py` | Domain and services can receive `today`; tests can freeze time |
| T1.5 | Security middleware: body size limit, CSRF (Origin + `X-PaySetu-Client`), security headers, in-memory rate limiter with named categories | `app/security/` | Tests: CSRF rejection, 429 with `Retry-After`, headers present |
| T1.6 | Storage service: write-once content-addressed store (stream to temp, SHA-256, rename, 0700 permissions), read stream, existence check | `app/storage/` | Tests: same bytes give the same key; overwrite impossible; the hash matches `hashlib` |
| T1.7 | Health endpoint becomes real (DB reachable, storage writable, adapter modes) | `app/api/v1/health.py` | Integration test passes |

- **Dependencies:** Phase 0.
- **DB/API changes:** Alembic baseline (no tables yet); `GET /health`.
- **Tests:** unit + integration for each task.

---

## Phase 2: Legal and Integrity Domain Core (pure logic)

**Goal:** the product's correctness core, as pure, fully tested functions with no I/O. **Can start in parallel with Phase 1.**

Legal readings are **not** decided here. Every tier I and C rule (PRD Section 4) is implemented as a named, configurable parameter in `msmed-v1.toml` with `counsel_confirmed = false`. Fixtures record `reviewed_by = "pending"`. T2.3 needs the owner to agree to building against the labelled defaults (DECISIONS.md LR-12 to LR-14). If counsel later changes a reading, only the rule-set values and fixtures change.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T2.1 | Rule set `msmed-v1.toml` (window 15, max agreed 45, multiplier 3, limitation 3 years, assumptions A1–A8, every PRD Section 4 rule ID with tier, explanation text and `counsel_confirmed` flag) + typed loader | `app/rules/msmed-v1.toml`, `app/rules/loader.py` (file I/O), `app/domain/rules.py` (pure validation) | The loader validates the file; unknown keys fail. **Done (M1-B)** |
| T2.2 | DeemedClock: `CaseFacts` + `today` → `ClockResult` (states, basis, window end, acceptance, due, interest start, limitation, 45-day cap, written vs verbal, objection inside/outside the window, phone-note objection not written, `other` channel counted as written, acknowledgement keeps the window open, multiple objections → latest removal, no holiday adjustment) | `app/domain/deemed_clock.py` | Fixture tests for every rule; worked example from PRD Section 4 passes; 100% branch coverage |
| T2.3 | Interest engine: monthly rests (rate/12), partial month days/365, half-up rounding to the paisa at each rest, rate in force at each period start, principal-first part payments, as-of date, period table | `app/domain/interest.py` | **Reference fixture: Rs 5,00,000 @ 17.25% × 12 months = Rs 93,406.72 (exact; about Rs 93,407)**; rate-change and part-payment fixtures pass; property test: interest is non-decreasing in the as-of date |
| T2.4 | Eligibility (R9, R9a, R10, R11) | `app/domain/eligibility.py` | All verdicts covered |
| T2.5 | Integrity: canonical JSON, event hash, chain verification, file-hash comparison result types | `app/domain/integrity.py` | Tamper tests (payload change, reorder, missing event) are detected |
| T2.6 | Checklist C01–C17 and next-action rules (DESIGN.md 9.4) | `app/domain/checklist.py`, `app/domain/next_action.py` | Table-driven tests for every item and each priority rule |
| T2.7 | Legal fixture format (`tests/fixtures/legal/*.toml` with a `reviewed_by` field) + a parametrised runner | `tests/fixtures/legal/`, `tests/unit/domain/` | Fixtures are human-readable for counsel review. **Done (M1-B).** Phase 2 status: T2.1–T2.7 complete; 100% line and branch coverage on `app/domain` (pytest-cov) |

- **Dependencies:** T0.2 only.
- **DB/API changes:** none.
- **Tests:** unit only; `mypy --strict` on `domain/`.

---

## Phase 3: Authentication and Supplier Profile

**Goal:** secure accounts, sessions and the supplier profile with eligibility.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T3.1 | Migration: `users`, `sessions` | `alembic/versions/…`, `app/models/` | Matches DATABASE.md 3.1–3.2 |
| T3.2 | Password hashing (Argon2id) + common-password check; session create/resolve/slide/revoke; `SupplierPrincipal` dependency | `app/security/passwords.py`, `app/security/sessions.py` | Unit tests incl. expiry (idle and absolute) and revocation |
| T3.3 | Endpoints: signup, login, logout, me, password change | `app/api/v1/auth.py`, `app/services/auth.py` | API.md 2.2 behaviour; generic errors; rate limits; cookie flags; tests for 401, CSRF, enumeration-safe messages |
| T3.4 | Migration: `suppliers`, `buyers` (buyers created here, used in Phase 4) | migrations, models | Matches DATABASE.md 3.4–3.5 incl. the composite unique |
| T3.5 | Supplier profile endpoints (`GET/PUT /supplier`) with computed eligibility; supplier-scoped repository base class | `app/api/v1/supplier.py`, `app/repositories/base.py` | Validation tests (Udyam, GSTIN, PIN); eligibility in the response |

- **Dependencies:** Phase 1, T2.4.
- **DB/API changes:** users, sessions, suppliers, buyers; `/auth/*`, `/supplier`.
- **Tests:** integration for all endpoints; session security tests.

---

## Phase 4: Buyers, Cases and Timeline

**Goal:** create and list buyers and cases, with every action recorded in a hash-chained, append-only timeline.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T4.1 | Buyer endpoints (list/search, create, get, patch, archive) | `app/api/v1/buyers.py`, service, repository | Cross-tenant 404 tests; duplicate GSTIN 409 |
| T4.2 | Migration: `cases`, `timeline_events` + append-only triggers | migrations | Trigger tests: UPDATE/DELETE on `timeline_events` fail |
| T4.3 | Timeline service: append event in the caller's transaction (seq allocation, canonical payload, chain hash) | `app/services/timeline.py` | Concurrency-safe seq (unique constraint test); chain verifies after N events |
| T4.4 | Case endpoints: create (reference allocation, rule-set version), get (with computed `clock`, `amounts`, `checklist_summary`, `next_action`), list (filters, urgency sort, cursor), patch (only before the first approval; `case_updated` event with old and new values), close/reopen | `app/api/v1/cases.py`, `app/services/cases.py` | API.md 2.5 shapes; backdated `recorded_late_days`; idempotency key on create |
| T4.5 | Dashboard endpoint (needs-attention rules + totals) | `app/api/v1/dashboard.py` | Tests with frozen time across states |

> **Note on later-phase inputs.** In Phase 4 the case service passes empty collections for evidence, responses, payments and communications, because those tables arrive in Phases 5, 6 and 9. Checklist items that depend on them report `missing`; payments default to none. Each later phase replaces its empty input with real data and extends the tests. No placeholder tables are created early.

- **Dependencies:** Phases 2 and 3.
- **DB/API changes:** cases, timeline_events; `/buyers/*`, `/cases/*`, `/dashboard`.
- **Tests:** integration (incl. cross-tenant) + trigger tests.

---

## Phase 5: Evidence Vault

**Goal:** upload, store, list, download, exclude and verify evidence, with the original bytes preserved.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T5.1 | Migration: `evidence_items` + triggers (exclusion-only update) | migrations | Trigger tests |
| T5.2 | Upload endpoint: streaming hash, magic-byte allowlist, size and case quota, duplicate detection, write file then row, `evidence_added` event | `app/api/v1/evidence.py`, `app/services/evidence.py` | Tests: allowed and rejected types, oversize 413, duplicate 409, bytes identical after download |
| T5.3 | List, download (attachment headers), exclude (`evidence_excluded` event) | same | Header tests; excluded items hidden by default |
| T5.4 | Supplier Udyam certificate upload (`/supplier/udyam-certificate`) → status `certificate_uploaded`. Supplier-level evidence (`case_id` NULL) creates no timeline event (DATABASE.md 3.9) | supplier service | Test incl. the partial unique index |
| T5.5 | Integrity check endpoint: re-hash all files + walk the chain; record `integrity_verified` / `integrity_failed` | `app/services/integrity.py` | **Tamper test: flip one byte in a stored file → `fail` naming that evidence item**; edited event row detected (trigger bypassed in the test via raw SQL with triggers dropped) |

- **Dependencies:** Phase 4, T1.6.
- **DB/API changes:** evidence_items; evidence endpoints; integrity-check.
- **Tests:** integration + tamper tests.

---

## Phase 6: Responses, Payments, Clock and Interest API

**Goal:** the facts that drive DeemedClock and interest, exposed through the API.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T6.1 | Migration: `buyer_responses`, `payments` + triggers | migrations | Matches DATABASE.md 3.7–3.8 |
| T6.2 | Responses endpoints (record, remove objection) → updated `clock` in the response; timeline events | `app/api/v1/responses.py` | Tests: objection in window → `objection_raised`; after Day 15 → labelled, no change; removal → acceptance moves |
| T6.3 | Payments endpoints (record, void, principal-exceed confirmation) | `app/api/v1/payments.py` | Tests incl. the settled state |
| T6.4 | Migration + seed: `bank_rates` from `seed/bank_rates.toml`; `GET /reference/bank-rates`, `GET /reference/rule-set` | migrations, `seed/`, `app/api/v1/reference.py` | Rate table version hash is stable |
| T6.5 | Interest endpoint (`/cases/{id}/interest?as_of=`) and checklist endpoint | `app/api/v1/cases.py` | Results equal the domain fixtures end-to-end |
| T6.6 | Generate the OpenAPI document and verify it is complete for Phases 3–6 | — | Schema includes every endpoint so far |

- **Dependencies:** Phases 4 and 5.
- **DB/API changes:** buyer_responses, payments, bank_rates; the endpoints listed.
- **Tests:** integration with frozen time.

---

## Phase 7: Frontend Foundation and Design System

**Goal:** the design system, app shell, API client and authentication pages. Can start after Phase 0 and connect to the API once Phase 3 lands.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T7.1 | Tailwind theme from DESIGN.md tokens (colors, type scale, spacing, radius, shadow); IBM Plex fonts via the framework font loader; global base styles. *Baseline already landed in Phase 0 (landing page); T7.1 reviews and completes it* | `src/app/globals.css` (Tailwind v4 `@theme`), `src/app/layout.tsx` | Token names match DESIGN.md exactly; no raw hex in components |
| T7.2 | Formatters: money (en-IN, Rs), dates (DD MMM YYYY, IST), hash shortening, relative dates | `src/lib/format/` | Unit-tested via Playwright component checks or a tiny test page (no new test framework) |
| T7.3 | API client: generated types (`openapi-typescript`), fetch wrapper (credentials, CSRF header, problem+json → typed errors, 401 → login redirect), upload with progress, `useApi` hook | `src/lib/api/`, `src/lib/hooks/` | Typecheck passes; errors map to fields |
| T7.4 | UI primitives: Button, inputs (Money, Date, Udyam, GSTIN, Select, RadioCards, Textarea), StatusBadge, HashChip, Toast, Skeleton, EmptyState, ErrorState, Banner, Dialog/Sheet, StepProgress, DataList | `src/components/ui/` | Each follows DESIGN.md Section 5 incl. focus, disabled, loading; a dev-only `/dev/components` page to review them |
| T7.5 | App shell: mobile bottom tabs + desktop sidebar, top bar, SimulatedBanner, OfflineBanner, DisclaimerFooter; middleware redirect | `src/components/layout/`, `src/middleware.ts` | Responsive at 360 and 1280; keyboard navigable |
| T7.6 | Public pages: landing, login, signup, legal placeholders (content marked "pending counsel review") | `src/app/(public)/` | Playwright: sign up → land on onboarding |
| T7.7 | Onboarding (3 steps) + settings (profile, signatory, password change) | `src/app/(app)/onboarding`, `/app/settings` | Eligibility summary renders all verdicts |
| T7.8 | Copy catalogue in `src/content/` used by all of the above | `src/content/` | No hard-coded user-facing strings in components |

- **Dependencies:** Phase 0; Phase 3 for live wiring.
- **DB/API changes:** none.
- **Tests:** Playwright auth + onboarding at both viewports; lint and typecheck.

---

## Phase 8: Frontend Core Case Flows

**Goal:** the supplier can do J2, J4, J5 (without letters), J7 and J9 in the UI.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T8.1 | Buyers list/detail + inline "quick create buyer" | `src/app/(app)/app/buyers/`, `src/components/buyers/` | Empty, loading and error states |
| T8.2 | New delivery form (mobile-first, sticky Save, camera capture, EvidenceUploader with progress → HashChip) | `/app/cases/new`, `src/components/evidence/EvidenceUploader.tsx` | **Playwright: log a delivery with a photo in ≤ 8 interactions at 360×800** |
| T8.3 | Case overview: NextActionCard, DayStrip, KeyDates with "Why?" LegalNotes, AmountSummary | `/app/cases/[id]`, `src/components/cases/` | Renders every clock state from seeded test cases; accessible DayStrip text |
| T8.4 | Case sub-navigation + Evidence tab (grouped list, exclude, verify integrity with StepProgress and mismatch report) | `/app/cases/[id]/evidence` | Tamper demo visible in the UI |
| T8.5 | Responses tab (record, tag, remove objection) and Payments tab (record, void, calculation table) | `/responses`, `/payments` | Clock updates after each action |
| T8.6 | Timeline tab and Checklist tab | `/timeline`, `/checklist` | Hash chips, late-record warnings; checklist actions deep-link |
| T8.7 | Case list (filters, search, urgency sort, cursor "load more") and Dashboard | `/app/cases`, `/app` | Empty and filter-empty states |

- **Dependencies:** Phases 6 and 7.
- **DB/API changes:** none expected. Any gap goes back to API.md first.
- **Tests:** Playwright journeys for J2, J4, J5 (payments), J7 and J9 at both viewports.

---

## Phase 9: Communications (Intimation and Demand)

**Goal:** draft → approve → send/record letters, with frozen content, PDFs and safe email.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T9.1 | Migration: `communications` + triggers, **without** `buyer_share_link_id` (added in T10.8) | migrations | Frozen-field trigger test |
| T9.2 | Templates `intimation-v1`, `demand-v1` (plain text with computed values; "draft wording pending advocate review" note) | `app/documents/templates/` | Snapshot tests of the rendered text |
| T9.3 | PDF rendering with ReportLab (DESIGN.md 12.12: header, footer, hash, DRAFT/SIMULATED marks, embedded Plex fonts) | `app/documents/pdf.py` | PDFs open; text is selectable; deterministic content hash for the same inputs |
| T9.4 | Endpoints: create draft, get, patch, approve (`content_sha256_seen`), record-manual, download PDF; timeline events | `app/api/v1/communications.py` | Approval mismatch → 409; profile signatory required |
| T9.5 | Email adapter interface + `SimulatedEmailSender` + `SmtpEmailSender` (timeout, Reply-To, PDF attachment); send endpoint with the conditional status transition | `app/integrations/email/` | **Test: send without approval is impossible; double send returns 409; SMTP failure → `send_failed`, approval kept** (SMTP mocked) |
| T9.6 | Frontend Letters tab: list, editor + preview, ApprovalReview dialog, send/record-manual, failure + retry | `/app/cases/[id]/communications` | Playwright J3 and the J5 demand |

- **Dependencies:** Phases 6 and 8.
- **DB/API changes:** communications; `/communications/*`.
- **Tests:** integration + Playwright. No real SMTP in tests.

---

## Phase 10: Sealed Pack, Share Links and Public Pages

**Goal:** export, advocate sharing and the Buyer Cost Page.

| Task | Description | Files / modules | Completion criteria |
| --- | --- | --- | --- |
| T10.1 | Migration: `sealed_packs`, `share_links`, `share_access_logs` + triggers | migrations | Trigger tests |
| T10.2 | Pack builder: integrity gate, PDFs (read-me, summary, timeline, s.63 DRAFT, counsel questions), byte-exact evidence copy, `manifest.json`, manifest hash, versioning | `app/documents/pack.py`, `app/services/packs.py` | **Test: unzip → re-hash every file → matches the manifest; manifest hash matches the DB**; blocked on integrity failure (409) |
| T10.3 | Pack endpoints (list, generate, download) | `app/api/v1/packs.py` | Download headers; rate limit |
| T10.4 | Share-link service: token generation, HMAC storage, purpose validation, consent for advocate links, expiry bounds, revoke, access log | `app/services/share_links.py`, `app/api/v1/share_links.py` | Raw token returned once only; tests for expiry and revocation |
| T10.5 | Public endpoints: buyer projection, advocate projection, pack download, advocate integrity check; no-store/noindex headers | `app/api/v1/public.py` | **Allowlist tests: the buyer projection contains no evidence, timeline or bank details**; invalid token = revoked message |
| T10.6 | Frontend Share tab (packs, advocate links, buyer links, access logs, revoke) | `/app/cases/[id]/share` | Playwright J8 |
| T10.7 | Public pages `/b/[token]` (print-friendly) and `/a/[token]` | `src/app/b/`, `src/app/a/` | Playwright J6 and the advocate flow; expired/revoked states |
| T10.8 | Embed the Buyer Cost link in demand letters: migration adds `communications.buyer_share_link_id`; the demand draft accepts it; the template renders the URL; the Letters tab offers "Include buyer link" | migrations, `services/communications.py`, `/communications` page | Test: the link must belong to the same case and be active; the approved letter freezes the URL text |
| T10.9 | Include supplier-level evidence (`07_supplier_documents/`) in packs | `documents/pack.py` | Manifest covers the Udyam certificate |

- **Dependencies:** Phase 9 (letters exist before the buyer link can be embedded in them). In Phase 9, demand letters ship without the link.
- **DB/API changes:** sealed_packs, share_links, share_access_logs; `/packs/*`, `/share-links/*`, `/public/*`.
- **Tests:** integration + Playwright.

---

## Phase 11: Demo Readiness, QA and Hardening

**Goal:** meet every PRD Section 15 demo criterion, with security and quality reviewed.

| Task | Description | Prompt | Completion criteria |
| --- | --- | --- | --- |
| T11.1 | Demo seed (`seed/demo.py`): Ravi supplier, buyers, three backdated cases, SAMPLE files; refuses to run in production | 9 | `make seed` creates a ready demo in < 10 s |
| T11.2 | Full Ravi journey end-to-end test (J2 → J8) + tamper demo at 360×800 | 14 | Passes in CI; total scripted time < 5 min |
| T11.3 | Accessibility pass (keyboard, focus, contrast, screen-reader labels on DayStrip/HashChip, reduced motion) | 14 | No WCAG 2.2 AA blockers on the critical screens |
| T11.4 | Security audit and fixes (authz on every endpoint, CSRF, uploads, headers, rate limits, logs, dependencies audit via `pip-audit`/`npm audit` run as tools, not added as deps) | 16 | No high or critical findings open |
| T11.5 | Code review and refactor against all documents | 17 | Findings fixed or recorded as debt |
| T11.6 | Update the root `README.md` (status, install, demo script) | — | Accurate to what was run |

---

## Phase 12: Deployment, Monitoring and Final Audit

**Goal:** a deployed demo/pilot environment on the approved hosting (D1), observable and recoverable.

| Task | Description | Prompt | Completion criteria |
| --- | --- | --- | --- |
| T12.1 | Server provisioning (Indian region), unprivileged user, Caddy, systemd units, production `.env` (outside the repo) | 18 | HTTPS works; health is green |
| T12.2 | Release procedure: install pinned dependencies → `alembic upgrade head` → build → restart → health check; documented in the README | 18 | One documented, repeatable release |
| T12.3 | Backups (DB `.backup` + storage sync, encrypted, off-server) + first restore test with a full integrity verification | 19 | Restore verified |
| T12.4 | Monitoring: uptime check on `/health`, structured log retention, alerts for 5xx spikes, `send_failed`, `integrity_failed` and disk > 80% | 19 | Alerts tested once |
| T12.5 | Final production audit → READY / READY WITH WARNINGS / NOT READY | 20 | Verdict recorded; simulated modes and pending counsel review listed as warnings |

---

## Phase 13: P1 Enhancements (only after MVP is stable)

| Task | Description | Notes |
| --- | --- | --- |
| T13.1 | Password reset (`password_reset_tokens`, forgot/reset endpoints and pages) | Needs SMTP |
| T13.2 | `.eml` upload with DKIM grading (`dkimpy`) + prefilled response | New dependency already listed in ARCHITECTURE.md |
| T13.3 | Udyam verification adapter (simulated + sandbox), labelled "simulated" | Prompt 13; needs provider keys |
| T13.4 | Data export and deletion request (DPDP) | Retention per D12 |

---

## Cross-Cutting Checks (every phase)

- Documents updated with any change (AGENTS.md Section 12).
- No new dependencies beyond ARCHITECTURE.md Section 2 without approval.
- Lint, typecheck and tests green before merge. Results are reported, not assumed.
- Simulated behaviour is labelled end-to-end.
- No legal logic outside `domain/` and the rule set.

---

## First Milestone: M1, "Runnable skeleton + legal core"

**Scope:** T0.1–T0.5 (repository, backend and frontend skeletons, Playwright smoke test, README update), then T2.1–T2.7 (rule set, DeemedClock, interest, eligibility, integrity, checklist, legal fixtures).

**Why this milestone is safe:**

- **No database.** M1 creates no schema, so there are no migrations to undo.
- **No personal data, auth or external services.** Nothing touches SMTP, a provider or a live server.
- **No package beyond the approved toolchain** (ADR-011).
- **No legal reading is fixed in code.** Every tier I and C rule is a labelled configurable parameter (ADR-013), so counsel feedback changes data, not architecture.
- **The riskiest logic is built first.** The rules engine carries the highest product risk, and it gets an objective pass/fail check: the Rs 93,407 reference fixture.

**Needs from the owner before starting:**

- **ADR-011 (toolchain):** approval, or a reply that the proposal is acceptable.
- **ADR-020 (Git workflow):** the same.
- **Building against labelled defaults:** agreement that T2.3 may use the defaults for LR-12 to LR-14.

**Exit criteria:**

- `make lint`, `make typecheck`, `make test` and `make e2e` all pass.
- 100% branch coverage on `backend/app/domain/`.
- All legal fixtures pass, with `reviewed_by = "pending"`.
- The README "Installation" section lists only commands that were actually run.

**How to run it:**

1. Prompt 8 (Project Setup) for T0.1–T0.5.
2. Prompt 9 (Feature Development) with the task set to "T2.1–T2.7 from docs/IMPLEMENTATION_PLAN.md".
