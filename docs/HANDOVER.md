# PaySetu: Project Handover

Snapshot taken 25 Oct 2026, after **removing the email-verification requirement** (Section 2b), on top of the final UI/UX redesign ("Warm Ledger") and Phase 7B (business onboarding), Phase 7A (email verification), Phase 6.1 (password reset, change and sessions) and Phase 6 (authentication and case-level authorisation). Verified against the workspace, not from memory. The previous handover's findings were audited in `docs/AUDIT_REPORT.md` (Section 9 records what was resolved).

## 1. Project overview

PaySetu helps Indian micro and small suppliers (Udyam-registered) keep provable evidence of a delivery and track the MSMED Act payment clock: acceptance date, due date, interest and a readiness checklist. It prepares and organises evidence; it is not a law firm, does not file claims and does not predict outcomes.

Source requirements: `docs/PRD.md`. Architecture: `docs/ARCHITECTURE.md`. Schema: `docs/DATABASE.md`. API contract: `docs/API.md`. Plan: `docs/IMPLEMENTATION_PLAN.md`. Decisions and legal review items: `docs/DECISIONS.md` (Phase 6: Section 8; 6.1: Section 9; 7A: Section 10; 7B: Section 11). Coding rules: `AGENTS.md`.

## 2. Git state

- Branch `backend`. Latest commit and **safety checkpoint**: `ba06e5d feat: implement supplier business onboarding` (the working tree was clean when the redesign started; `git diff ba06e5d` shows everything the redesign changed, and `git checkout ba06e5d -- frontend docs` restores the previous frontend and docs if needed).
- **The redesign is not committed.** It changes the frontend, `docs/DESIGN.md`, this handover and `docs/screenshots/`, plus two whitespace-only reformats in `backend/app/storage/` (see Section 2a). Nothing has been pushed.
- Suggested commit grouping: (1) design tokens and shared components; (2) landing, dashboard and case workspace; (3) session-check fix and tests; (4) docs and screenshots; (5) the two backend formatting-only changes.

## 2a. Final redesign (25 Oct 2026)

**Visual direction.** "Warm Ledger" (DESIGN.md v1.3): warm white surfaces, charcoal type, black primary buttons, one orange accent, a faint peach gradient only on the landing hero and the sign-in pages, thin borders and hairline shadows, Geist type. Based on your written direction and the general style of the Aceternity Schedule marketing template; no screenshot was attached to the request and no template assets or branding were copied. Every token pair used for text meets WCAG AA; the bright orange `#F28B53` (2.4:1) is used decoratively only, with `#D9622A` for large headline emphasis and `#A4471A` for orange text (DESIGN.md 2.1).

**What changed (frontend only; no API, database or legal-engine change).**
- Global tokens replaced (`globals.css`); `brass` renamed `accent`; a shared `Wordmark`; softer secondary buttons; hairline card shadow.
- **Landing page rebuilt:** minimal navbar (How it works, Features, Sign in, Create account), headline "Every payment has a *deadline.* / Every business deserves clarity.", one primary hero action, a framed product preview, a five-step workflow, a bento section for the five tools, "What PaySetu is not" and "Honest by design", and a footer. All figures are labelled sample content; the sample timeline mirrors the rules engine (deemed acceptance on the delivery day).
- **Dashboard rebuilt:** a single **Recommended next step** for the most urgent case (overdue, then objection, then nearest due date), using that case's real `next_action` and checklist readiness from `GET /cases/{id}`; tracked principal, cases needing attention, payments due in 30 days; upcoming deadlines with days remaining; needs-attention and recent cases; business-profile status; eligibility. One primary action per view (the sidebar and header "Record delivery" are now secondary).
- **Case workspace:** DeemedClock gains a plain-language glossary ("What these terms mean") written from the rule set's own explanations; Interest gains "How this figure is worked out"; Record delivery is framed as three guided questions; the shell, tabs and cards use the new tokens.
- **Copy fix:** when the backend's next action was `generate_pack`, the UI still said pack export was "not available in this demo build yet"; it now points to the existing Evidence Pack.
- **Bug fix (found during screenshots):** if the workspace's session check (`GET /auth/me`) failed for any reason (for example a 429 from the 300 requests/minute per-user limit, or a network error), the user was sent to the sign-in page as if signed out. Now only a 401 does that; other errors show the message with **Try again**.
- **Auth, settings and onboarding** take the new visual language through the shared tokens and components; their behaviour is unchanged.

**Route-to-API matrix (every screen checked against the code and the e2e suite).**

| Route / action | Backend call(s) | Real behaviour verified by |
| --- | --- | --- |
| `/` landing | none (static; sample content labelled) | `smoke.spec`, `redesign.spec` |
| `/signup` | `POST /auth/signup` (then verification email in the outbox) | `auth.spec` |
| `/login` | `POST /auth/login` | `auth.spec`, `passwords.spec` |
| `/forgot-password`, `/reset-password` | `POST /auth/forgot-password`, `POST /auth/reset-password` | `passwords.spec` |
| `/app` dashboard | `GET /supplier`, `GET /cases`, `GET /onboarding`, `GET /cases/{id}` (focus case) | `redesign.spec`, `smoke.spec` |
| `/app/cases` | `GET /cases` | screenshots, `demo-journey.spec` |
| `/app/cases/new` | `GET /buyers`, `POST /buyers`, `POST /cases` | `demo-journey.spec` (incl. server validation) |
| Case overview (DeemedClock, amounts, next step) | `GET /cases/{id}`, `GET /cases/{id}/responses` | `demo-journey.spec`, `redesign.spec` |
| Evidence Vault | `GET/POST /cases/{id}/evidence`, `GET /evidence/{id}/download`, `POST /cases/{id}/integrity-check` | `demo-journey.spec`, `evidence-pack.spec` |
| Buyer responses | `GET/POST /cases/{id}/responses`, `POST …/remove-objection` | `demo-journey.spec` |
| Case Strength | `GET /cases/{id}/checklist` | `demo-journey.spec` |
| Interest | `GET /cases/{id}/interest?as_of=` | `demo-journey.spec` |
| Timeline | `GET /cases/{id}/timeline` | `demo-journey.spec` |
| Evidence Pack download | `GET /cases/{id}/evidence-pack` (refused on integrity failure) | `evidence-pack.spec` (ZIP and manifest checked; tamper refused) |
| `/app/onboarding` | `GET /onboarding`, `PUT /onboarding/draft`, `POST /onboarding/certificate`, `GET /onboarding/certificates/{id}/download`, `POST /onboarding/submit` | `onboarding.spec` |
| `/app/settings` | `GET /onboarding`, `POST /auth/change-password`, `POST /auth/logout-all` | `passwords.spec` |
| `/app/review`, `/app/review/{id}` (reviewers) | `GET /review/submissions`, `GET /review/submissions/{id}`, `…/certificate`, `POST …/checks`, `POST …/decision` | `review.spec`, backend `test_review.py` |
| Sign out | `POST /auth/logout` | `auth.spec` |
| Cross-user isolation | every case and onboarding route answers 404 for another supplier | `auth.spec`, `onboarding.spec`, backend `test_authorisation.py` |

Not available, and shown honestly: any official Udyam check (reviews are manual and labelled so), letters and payments (C11 and C13 always missing), share links and the Buyer Cost Page.

**Demo walkthrough (about 6 minutes).**
1. `/`: the headline, the sample product preview and its label, the five steps, "What PaySetu is not".
2. **Create account** → the dashboard opens directly (empty).
3. **Record delivery** (three guided questions; use a delivery date about 20 days ago and the inline **Add a buyer**) → case overview: DeemedClock timeline, **What these terms mean**, **Why this date?**, amounts with the unverified-rate warning.
4. **Evidence** → upload an invoice PDF → its SHA-256 → **Verify integrity** → "Integrity check passed".
5. **Case Strength** (what is met and missing) → **Interest** (worked example and assumptions) → **Timeline** (hash-chained events).
6. **Overview** → **Download Evidence Pack** → open the ZIP: README, summaries, original file, `manifest.json`.
7. **Dashboard** → the **Recommended next step** for that case.
8. **Business profile** → fill the form, upload a certificate PDF, **Save draft**, **Review & submit** → Pending review.
9. **Settings** → business status; **Sign out**. Optional: **Forgot password?** with `make email-outbox`.

Rehearsal tips: run `make migrate && make seed` beforehand. The 300 requests/minute per-user limit is reached only by automated loops, not by a person clicking through the demo. Use `npm run build && npm start` for the demo if possible: the development server shows a Next.js badge and compiles pages on first visit.

**Screenshots:** `docs/screenshots/` holds landing, dashboard, case overview, Evidence Vault and onboarding at 1440 px, and landing, dashboard and case overview at 360 px (real backend data from a test account; landing content is labelled sample). All 16 screens were also checked at 360, 390, 768, 1280 and 1440 px: no horizontal overflow, and every screen showed the intended page.

## 2b. Email verification removed as a requirement (owner-directed)

- **Base:** commit `d9717db` (redesign; tree was clean). Not committed.
- **Removed:** the backend gate (403 `email_not_verified`) on all case-workspace and onboarding routes (they use the session principal again; ownership scoping untouched); the verification email at signup; `POST /auth/verify-email` and `POST /auth/resend-verification`; their schemas, template, rate-limit categories and the `EMAIL_VERIFICATION_HOURS` setting; `DEMO_ACCOUNT_VERIFIED`; the frontend confirmation screen, resend button, "I have confirmed my email", `/verify-email` page, Settings verification badge and resend card, and the "Confirm email" navigation.
- **Kept:** the `email_verification_tokens` table, `users.email_verified_at` and all their rows (no migration); `user.email_verified` in auth responses (informational); password reset still records the inbox as verified, as before. Everything else (auth, sessions, CSRF, rate limits, ownership, onboarding, the five modules, the design) is unchanged.
- **Tests changed (only those affected):** `test_verification.py` became `test_email_verification_removed.py` (8 tests: signup and login reach the workspace at once, existing unverified accounts and their records, endpoints gone, unauthenticated still 401, no route answers `email_not_verified`, password reset unchanged); the authorisation suite's second supplier and the onboarding suite's users no longer verify first (all 404/ownership assertions kept); onboarding's "needs a verified email" test now checks "needs a session"; the signup verification email was dropped from the password log test's expected deliveries; the rate-limit and config tests lost the removed entries. E2E: `verification.spec.ts` became `no-email-verification.spec.ts` (signup and login go straight to the dashboard; an unverified account uses its own APIs while anonymous requests get 401; `/verify-email` and its API answer 404; the demo account works); `auth.spec` signup now lands on the dashboard; the helper no longer verifies.
- **Results:** `make lint`, `make typecheck` (mypy on 102 files, tsc) and `make build` pass; `make test` **574 passed** (300 integration, 274 unit), domain coverage 100%; Playwright **56/56 with `--workers=2`, twice in a row** (47 s and 42 s).
- **Security note:** without verification, anyone can sign up with an address they do not control. Restore verification (commit `578c865`) or an equivalent control before any real-user use.

## 2c. Light and dark themes (25 Oct 2026)

Frontend-only. Dark mode overrides the existing semantic tokens (DESIGN.md 2.3); light mode is unchanged. Preference light / dark / system is saved per device (`localStorage`) and never sent to the backend; `public/theme-init.js` applies it before first paint. Controls: Sun/Moon toggle in the app top bar and a Theme card in Account settings. Tests: `frontend/tests/e2e/theme.spec.ts` (switching and persistence, system preference, no flash and no hydration warnings, and a 16-page dark sweep that fails on any white background or light-theme text colour).

## 2d. Phase 7C: secure business review (26 Oct 2026)

- **Reviewer role:** append-only `reviewer_grants`, issued and revoked only by the operator CLI (`make reviewer ARGS='create --email … --name "…"'`, also `grant`, `revoke`, `list`). Signup and API payloads can never grant it. Reviewer-only staff accounts have no supplier workspace; a supplier granted the role keeps theirs but cannot review their own business.
- **Workflow:** `/app/review` queue (pending by default; filters; cursor pagination) → submission detail: frozen snapshot, snapshot and certificate integrity, certificate download (attachment), other claims on the same Udyam number, manual checks (source, what was consulted, date, per-field submitted vs seen vs result), decision (approve, reject or request information, with a reason and an optional internal note), full history. Decisions are final; NEEDS_INFORMATION reopens the supplier's draft and a resubmission is a new, separate snapshot.
- **Honesty:** three evidence levels (supplier-submitted only, manually reviewed, matched an official record by manual check); no Udyam or government integration exists; "Approved" is a reviewer decision, never a government verification. `VERIFIED` was renamed `APPROVED` (migration `3d7a9c1e5b20`).
- **Supplier side:** Business profile shows the decision, the reason (for Needs information and Rejected), and the submission history with each outcome. Eligibility, cases and packs are unaffected.
- Decisions and design: DECISIONS.md Section 13. API: API.md "Business review". Tables: DATABASE.md 3.3c.

## 3. Completed features

**Backend (FastAPI 0.162, SQLite, SQLAlchemy 2.1.6, Alembic 1.20.1):**
- Platform: typed settings with a production gate, database and migrations, problem+json errors, request IDs, redacting JSON logs, injectable clock, body limit, CSRF, security headers, in-memory rate limits.
- Supplier routes: buyers, cases, buyer responses, evidence upload and download, integrity check, timeline, checklist, interest, evidence-pack ZIP (Section 5).
- **Phase 6, authentication:** signup (creates user, supplier and session together), login, logout, me. Argon2id password hashes (`argon2-cffi` 25.1.0), 10 to 128 characters, common passwords refused. 256-bit session tokens stored only as SHA-256, in an HttpOnly, SameSite=Lax cookie (Secure on https). Sessions expire after 7 idle days (sliding, refreshed at most hourly) or 30 days after login, and on logout. Login revokes any earlier session in the browser. Login and signup errors are generic, and an unknown email still costs one Argon2 check. Rate limits: login 5/min per IP+email and 20/hour per IP, signup 5/hour per IP, 300/min per user on other routes.
- **Phase 6.1, passwords and sessions:** forgot password (always the same 202 answer; email sent after the response), reset password (single-use, 15-minute token stored only as HMAC; consumed atomically with the password change; every session revoked; no automatic sign-in), change password (current password required; reuse of the current one refused; every session revoked and this browser given a new one), sign out everywhere. Confirmation emails after every change, with an honest `sent`/`failed` result. Email through `app/mail/`: a development file outbox (`STORAGE_DIR/outbox/*.eml`, `make email-outbox`) or SMTP.
- **Phase 7A, email verification:** built, then **removed as an access requirement** at the owner's request (Section 2b; DECISIONS.md Section 12). Signup and login open the dashboard directly; ownership checks are unchanged.
- **Phase 7B, business onboarding:** draft business profile (enterprise name, Udyam number normalised to `UDYAM-XX-00-0000000`, self-declared micro/small/medium, optional registration date, registered address, contact, representative and role, authorisation note and confirmation; no Aadhaar, PAN or bank data); private PDF certificate upload (5 MB, structural PDF checks, active content refused, SHA-256, separate `STORAGE_DIR/business/` store, owner-only attachment downloads, replacement keeps old files); submission to **PENDING_REVIEW** with an immutable snapshot; duplicate Udyam numbers recorded as **contested** claims for review instead of being rejected. No supplier route can set NEEDS_INFORMATION, VERIFIED or REJECTED. Business status is separate from case eligibility and is not required for the case workspace.
- **Phase 6, authorisation:** one dependency resolves the cookie to `SupplierPrincipal(user_id, supplier_id)` on every supplier route. Services scope every query by that `supplier_id`, so another supplier's case, buyer, response, evidence file, download, timeline, interest, integrity check or pack answers 404, and writes leave the case untouched. Owner IDs in request bodies are rejected.

**Frontend (Next.js 16.4.3, React 19.3, Tailwind 4):**
- "Oxford Blue + Stone" design system (Geist), committed in `3175836`: landing page, dashboard, cases, Record delivery, case workspace (Overview with the DeemedClock timeline and the evidence pack, Evidence Vault, Buyer responses, Case Strength, Interest, Timeline).
- **Phase 6:** `/login` and `/signup` pages with field-level errors and loading states. A session guard on `/app/*` sends signed-out visitors to `/login?next=…`, and back afterwards (only `/app` paths are accepted). A session that ends mid-use leads to `/login?reason=expired` with an explanation. The sidebar and mobile menu show the user and business and a **Sign out** button.
- **Phase 6.1:** `/forgot-password` and `/reset-password` pages (the token is read from the URL fragment once, removed from the address bar and kept only in memory; missing, invalid and expired-link states). **Account settings** (`/app/settings`, new sidebar item): account details, Change password, and Sign out everywhere with a confirmation step. "Forgot password?" on the sign-in page.
- **Phase 7B:** `/app/onboarding` (sidebar **Business profile**): sectioned form with Udyam format guidance and live normalisation preview, certificate upload with a progress bar, Save draft, Review & submit, submission confirmation and history (snapshot fingerprints, contested flag); Account settings show the business status.
- **Phase 7A:** the confirmation screen, resend button and `/verify-email` page were removed with the requirement (Section 2b).
- Accessibility (audit F3): a `control` token for input boundaries (3:1 or more on every surface); brass removed from small text; the contrast table is recomputed in DESIGN.md 2.1.

**Domain engine (pure Python, `backend/app/domain/`, 100% line and branch coverage):** unchanged in Phase 6.

## 4. Status of the five core modules

| PRD module | Status | Notes |
| --- | --- | --- |
| **DeemedClock** | Implemented in domain, API and UI | Computed on every read; only written objections change acceptance. Legal readings are provisional (Section 11) |
| **Evidence Vault** | Partly implemented | Upload, SHA-256, owner-only download, append-only timeline, integrity check. Missing: `.eml` DKIM grading, RFC 3161 timestamps, exclusion route |
| **Case Strength** | Implemented in domain, API and UI | Checklist C01–C17; C11 and C13 always missing (letters not built) |
| **Buyer Cost Page** | Not built | Only the interest figure exists; no share links |
| **Sealed Pack** | Partly implemented | On-demand ZIP export for the case owner only; not stored or versioned; no PDF, no s.63 draft |

## 5. API endpoints (`/api/v1`)

| Method | Path | Auth | Mounted |
| --- | --- | --- | --- |
| GET | `/health` | none | always |
| POST | `/auth/signup`, `/auth/login` | none (rate-limited, CSRF headers required) | always |
| POST | `/auth/logout` | cookie if present; idempotent 204 | always |
| GET | `/auth/me` | session | always |
| POST | `/auth/forgot-password` (3/hour per IP+email, 10/hour per IP) | none; always 202 | always |
| POST | `/auth/reset-password` (10/hour per IP) | reset token in the body | always |
| POST | `/auth/change-password` (5 per 15 min per user) | session | always |
| POST | `/auth/logout-all` | session | always |
| GET | `/onboarding`, `/onboarding/submissions` | verified session, own data | not in production |
| PUT | `/onboarding/draft` | verified session; 409 once submitted | not in production |
| POST | `/onboarding/certificate` (PDF ≤ 5 MB, 20/hour per user) | verified session | not in production |
| GET | `/onboarding/certificates/{id}/download` | verified session, owner only (else 404) | not in production |
| POST | `/onboarding/submit` | verified session; DRAFT/NEEDS_INFORMATION → PENDING_REVIEW only | not in production |
| GET | `/supplier` | session | not in production |
| GET, POST | `/buyers` | session, own buyers only | not in production |
| GET, POST | `/cases` | session, own cases only | not in production |
| GET | `/cases/{id}`, `/cases/{id}/checklist`, `/cases/{id}/interest?as_of=`, `/cases/{id}/timeline` | session, owner only (else 404) | not in production |
| GET, POST | `/cases/{id}/responses`; POST `/cases/{id}/responses/{rid}/remove-objection` | session, owner only | not in production |
| GET, POST | `/cases/{id}/evidence` (upload 15 MB, 30/min per user) | session, owner only | not in production |
| GET | `/evidence/{id}/download` | session, owner only | not in production |
| POST | `/cases/{id}/integrity-check` | session, owner only | not in production |
| GET | `/cases/{id}/evidence-pack` (5/hour per supplier and case) | session, owner only | not in production |

All supplier routes above need a session and are owner-scoped (no email-verification requirement). All writes need `Origin` equal to `PUBLIC_BASE_URL` and `X-PaySetu-Client: web`. The supplier routes stay unmounted in production while the legal rules await review (DECISIONS.md Section 8).

## 6. Database and migrations

- Revisions: `bf48eb38df15` (baseline) → `7f9909eb7e4c` (demo case core) → `099b88746350` (accounts and ownership) → `d71bd50903a9` (password reset tokens, Phase 6.1) → `5c2e8a41f0b7` (email verification) → `8e1f3c9a2b64` (business onboarding, Phase 7B: four new tables with SQLite triggers; no existing row changed; every existing supplier is NOT_STARTED) → **`3d7a9c1e5b20` (business review, Phase 7C: `reviewer_grants`, `business_checks`, `business_check_items`, `business_reviews` with SQLite triggers; `business_profiles` rebuilt to rename the unused `VERIFIED` status to `APPROVED`; no grant created)**. Email verification (7A) added `users.email_verified_at` added with `ALTER TABLE ADD COLUMN`, plus `email_verification_tokens`; every existing user stays unverified; no session revoked; no row changed)**. Accounts and ownership added `users`, `sessions`, `suppliers.owner_user_id` (nullable, unique; only a demo supplier may be unowned, enforced by triggers on SQLite and a CHECK on PostgreSQL).
- **Existing data:** the migration assigns no row to anyone. The seeded demo supplier stays unowned and unreachable until `DEMO_ACCOUNT_PASSWORD='…' make demo-account` gives it a login (default email `demo@paysetu.example`; refuses production; claims only an unowned demo supplier; the password is never printed).
- **Local database migrated (Phases 6, 6.1, 7A, 7B, 7C):** backed up before each migration (`paysetu.db.pre-phase6.bak`, `.pre-phase6_1.bak`, `.pre-phase7a.bak`, `.pre-phase7b.bak`, `.pre-phase7c.bak`; git-ignored). Before and after `3d7a9c1e5b20` (26 Oct) the row counts were identical: 3 users, 9 sessions, 3 suppliers, 2 buyers, 5 cases, 5 evidence items, 21 timeline events, 2 responses, 0 business profiles, submissions, certificates and claims; no reviewer grant exists until one is created with `make reviewer`. Before and after `8e1f3c9a2b64` the row counts were identical: 2 users (both still unverified), 2 sessions, 2 suppliers (`self_declared`), 1 buyer, 3 cases, 3 evidence items, 16 timeline events, 2 responses, 1 verification token; 0 business profiles.
- **How existing accounts complete verification:** sign in → confirmation screen → Send a new link → open the emailed link → Confirm my email. A completed password reset also confirms the email.

## 7. Test results (run 25 Oct 2026, final code)

| Check | Result |
| --- | --- |
| `make lint` (ruff check + format, eslint, prettier) | Pass |
| `make typecheck` (mypy strict on 87 files; tsc) | Pass |
| `make test` | **593 passed** (318 integration, 275 unit), 1 warning (Starlette notice about `httpx2`); domain coverage 100% line and branch. Unchanged by the redesign (no backend logic change) |
| `make lint`, `make typecheck` (mypy strict on 102 files; tsc) | Pass. Lint found one over-long line in `business_store.py` (Phase 7B): ruff had never checked that file because it was git-ignored until the `.gitignore` fix. Fixed by reformatting (whitespace only, together with one line in `evidence_store.py`) |
| `make build` (Next.js) | Pass |
| Playwright e2e (56 tests = 28 × 360×800 and 1280×800; real backend) | **Final code: 56/56 with `--workers=2`, twice in a row** (1.4 and 1.5 min). New `redesign.spec.ts` (4 tests × 2): dashboard next step and figures match `GET /cases/{id}` and the CTA opens the case; DeemedClock glossary; landing labels sample content and has one hero primary action; a 429 on the session check is shown with Try again instead of a sign-out (the only simulated response in the suite) |
| Earlier runs during the redesign (honest record) | Six full runs before the final two: four were all green; one had a single failure where the Next.js dev proxy dropped the login request (network error, the page correctly said it could not reach the server); one had a single failure in the password-reset test whose cause was not captured before the next run overwrote it. A deliberate stress run (`auth.spec` repeated 3 times against one backend) failed 8 logins with **429**: the 20 logins/hour per-IP limit working as designed. A normal full run makes about 18 logins from 127.0.0.1, so that limit has little headroom as the suite grows (Section 12) |

**Phase 7C run (26 Oct 2026).** `make lint` and `make typecheck` (mypy on 112 files; tsc): pass. `make test`: **620 passed**, 1 warning (Starlette `httpx2` notice); domain coverage 100% line and branch (`business_review.py` 100%). `make build`: pass (`/app/review`, `/app/review/[id]`). Playwright `--workers=2`, 70 tests: `review.spec.ts` 6/6 on its own; full run **66 passed, 4 failed**: one 429 from the login limit above, three 30-second timeouts at a load average near 40. Rerunning those four spec files: 23 passed and 1 failed on a dropped dev-proxy connection (`ECONNRESET`, the known flake); `demo-journey.spec.ts` then passed 6/6.

**Phase 7D run (26 Oct 2026).** `make lint`, `make typecheck` (mypy on 112 files; tsc), `make build`: pass. `make test`: **628 passed** (8 new login-limit tests), 1 warning (Starlette `httpx2` notice); domain coverage 100%. Playwright `--workers=2`, 70 tests, six full runs after the fix: run 1 (login fix only) 69/70 (first-visit compile timeout); run 2 70/70; run 3 69/70 (`ECONNRESET` on `/auth/me`); after the keep-alive fix, runs 4, 5 and 6 **70/70 each**, with 0 proxy resets and 0 rate-limit responses.

## 8. Commands

```bash
make setup                 # backend venv + pip; frontend npm ci + Playwright Chromium
cp backend/.env.example backend/.env   # then set local values (never commit)
make migrate               # alembic upgrade head
make seed                  # synthetic demo supplier, sample buyer, unverified bank rate
DEMO_ACCOUNT_PASSWORD='…' make demo-account   # optional login for the demo supplier
make dev                   # API :8000 + web :3000; sign up or sign in at http://localhost:3000
make lint | make typecheck | make test | make build | make e2e
make api-types             # regenerate frontend types after any API change
make email-outbox          # newest development emails: verification and reset links (refuses production)
make reviewer ARGS='create --email reviewer@example.com --name "A Reviewer"'   # hidden password prompt
make reviewer ARGS='list'  # also grant / revoke --email …
```

Local email testing (forgot and reset password): README.md, "Local email testing".

`make e2e` starts its own backend on :8100 (fresh database, `APP_ENV=test`, `AUTH_SIGNUP_LIMIT_PER_HOUR=200`, `AUTH_LOGIN_IP_LIMIT_PER_HOUR=200`, a demo account and a reviewer with test-only passwords) and Next on :3100 (`.next-e2e`). On a busy machine run `cd frontend && npx playwright test --workers=2`.

## 9. Security limitations (do not claim production-ready)

- **Production is not supported yet.** The supplier routes are unmounted in production, the legal rules are unreviewed, and the evidence pack is labelled an evaluation export.
- **Business review (Phase 7C) is manual.** There is no official Udyam check; a reviewer records what they looked up by hand. No email tells the supplier about a decision (they see it in the app), there is no two-person approval and no way to reopen a final decision, and certificate downloads by reviewers are not individually logged. Whoever can run `tools/reviewer.py` against the database can grant the role: protect database access accordingly. No malware scanning of uploaded PDFs (they are never opened or rendered by PaySetu, only stored and returned as attachments). PDF checks are structural, not a full parser. The registered address and contact details are personal data in a sole proprietorship; retention rules (PRD D12) still apply.
- **Email verification proves inbox control only.** It is not business, Udyam or MSMED verification and grants nothing else. There is no email-change feature yet (tokens already stop working if the address changes), no reminder emails and no expiry of never-verified accounts. Verify-email is unauthenticated by design (120/hour per IP); tokens are 256-bit, so guessing is not practical.
- **Password reset and change are built (Phase 6.1); account deletion is not.** Reset needs working email: with `EMAIL_MODE=simulated` links exist only in the local outbox. Only the current password is checked against reuse (no password history). Forgot-password responses for real and unknown accounts differ by a few milliseconds because only a real account gets a database write; email delivery itself is outside the response.
- **Rate limits and lockout are in memory and per process.** They reset on restart and do not cover multiple instances. There is no per-account lockout beyond 5 attempts per minute per IP+email.
- **Common-password list is small** (bundled, about 40 entries). No breached-password check, no 2FA, no email verification: anyone can sign up with an address they do not own.
- **Signup consent is an evaluation notice**, not counsel-reviewed Terms or a Privacy Notice (no DPDP-grade consent record).
- **Client IP** comes from the socket peer. Behind a reverse proxy every user would share one IP for rate limits until trusted-proxy handling is added.
- **Browser guard is UX only** (no Next.js middleware). Pages render a loading state, then redirect; all authorisation is on the API.
- **CSRF** relies on the Origin or Referer check plus a custom header and SameSite=Lax (no token). Sound for same-origin deployment as designed, not for cross-origin embedding.
- **Timeline events record no user ID** (`actor_id` is null). Audit attribution beyond "supplier user" needs a follow-up.
- **Evidence download links** (`/api/v1/evidence/{id}/download`) are plain links; after a session ends, clicking one shows a JSON 401 instead of the login page.
- Not yet run: dependency audits (`pip-audit`, `npm audit`), a penetration test, a review against an external checklist.

## 10. Demo and evaluation limits

- Synthetic data only; the UI and signup notice say not to enter real business or personal data.
- Letters and payments not built (C11, C13 missing; paid amount zero).
- Bank rate unverified: only 5.75% from 7 Oct 2026 is recorded; earlier periods report "rate data unavailable".
- New accounts start with no buyers and an incomplete profile (eligibility "cannot assess"); there is no onboarding or profile editing yet (Phase 7 covers Udyam).

## 11. Pending legal review

Advocate review is required before any non-demo use. Full register: `docs/DECISIONS.md` Section 3 (LR-01 to LR-25). Key items: LR-01 to LR-07 (day counting, objections, 45-day cap); LR-12 to LR-14 (interest mechanics, bank-rate selection, payment allocation; provisional simulation defaults only); LR-16 (Section 63 certificate, none generated); LR-21 to LR-25 (MSMED Amendment Act 2026 enacted text and commencement). Rule set: `backend/app/rules/msmed-v1.toml`.

## 12. Known issues and technical debt

- **E2E login limit: fixed in Phase 7D** (DECISIONS.md Section 14). The e2e backend runs with `APP_ENV=test` and `AUTH_LOGIN_IP_LIMIT_PER_HOUR=200`; development and production refuse a raised value. A full run makes 21 logins.
- **E2E infrastructure fixes (Phase 7D):** global setup compiles every route before the tests (first-visit `next dev` compiles had exceeded 5-second assertions under load), and the e2e backend uses `--timeout-keep-alive 75` (uvicorn's 5-second default raced the dev proxy and produced `ECONNRESET`). Heavy host load can still slow runs.
- E2E runs against the Next.js **dev** server: occasional timing failures and one dropped proxy connection were seen under load. A production-build web server for Playwright would remove that class of flake.
- E2E timing on a loaded host with 4 workers (Section 7). Options: run e2e against `next build && next start` instead of `next dev`, or default to 2 workers.
- React development mode runs effects twice, so every page fetch is doubled in dev (not in production builds).
- Case references and timeline sequence numbers use read-then-insert with a bounded retry; replace with database sequences before multi-process deployment.
- Frontend copy is partly inline (AGENTS.md Section 4); no upload progress bar.
- Coverage gate covers only `app/domain`.

## 13. Recommended next tasks (priority order)

1. **Owner review and commit** of Phase 7B, starting with the `.gitignore` / `backend/app/storage/` repository fix (Section 2).
1a. **After Phase 7C:** supplier email notifications of decisions; decide (with legal review) whether an approved profile may update eligibility; optional two-person approval and certificate-access logging; any official Udyam check only through a sanctioned API.
2. **Auth completion:** account deletion request, email change (re-verification), record `actor_id` on new timeline events; configure a real SMTP relay before any non-local use.
3. **Phase 7:** onboarding and supplier profile editing, then Udyam verification.
4. **E2E stability:** production-build web server for Playwright, or 2 workers by default.
5. **Security hardening (T11.4):** `pip-audit` and `npm audit` as tools, trusted-proxy IP handling, shared rate-limit store before multiple instances.
6. **Legal:** advocate review of LR items; decide on the s.63 template.
7. Sealed Pack persistence, letters, share links and the Buyer Cost Page (Phases 9 and 10).

## 14. Resume checklist for the next session

1. `git status`; commit Phase 6 deliberately (Section 2).
2. `make migrate` on any local database, then `make demo-account` if the seeded demo data is needed.
3. `make test` and `make e2e` (or `--workers=2`); both passed as described in Section 7.
4. Read `docs/DECISIONS.md` Section 8 before changing auth or ownership.
