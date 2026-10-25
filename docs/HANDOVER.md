# PaySetu: Project Handover

Snapshot taken 25 Oct 2026, after Phase 7A (email verification and account activation), on top of Phase 6.1 (password reset, change and sessions) and Phase 6 (authentication and case-level authorisation). Verified against the workspace, not from memory. The previous handover's findings were audited in `docs/AUDIT_REPORT.md` (Section 9 records what was resolved).

## 1. Project overview

PaySetu helps Indian micro and small suppliers (Udyam-registered) keep provable evidence of a delivery and track the MSMED Act payment clock: acceptance date, due date, interest and a readiness checklist. It prepares and organises evidence; it is not a law firm, does not file claims and does not predict outcomes.

Source requirements: `docs/PRD.md`. Architecture: `docs/ARCHITECTURE.md`. Schema: `docs/DATABASE.md`. API contract: `docs/API.md`. Plan: `docs/IMPLEMENTATION_PLAN.md`. Decisions and legal review items: `docs/DECISIONS.md` (Phase 6: Section 8; Phase 6.1: Section 9; Phase 7A: Section 10). Coding rules: `AGENTS.md`.

## 2. Git state

- Branch `backend`. Latest commit: `08a5e11 feat: implement password recovery and account security` (Phase 6.1, committed by the owner).
- **Phase 7A is not committed.** `git status`: 35 modified and 5 untracked entries (new: migration `5c2e8a41f0b7`, `test_verification.py`, the `/verify-email` page, `frontend/src/components/account/`, `verification.spec.ts`). Nothing has been pushed.
- Suggested commit grouping: (1) backend: migration, model, verified-email dependency, verify and resend routes, template, rate limits, setting, demo-account option, tests, `.env.example`; (2) frontend: verification screen, `/verify-email`, settings status, shell navigation, API client Retry-After, e2e; (3) docs.

## 3. Completed features

**Backend (FastAPI 0.162, SQLite, SQLAlchemy 2.1.6, Alembic 1.20.1):**
- Platform: typed settings with a production gate, database and migrations, problem+json errors, request IDs, redacting JSON logs, injectable clock, body limit, CSRF, security headers, in-memory rate limits.
- Supplier routes: buyers, cases, buyer responses, evidence upload and download, integrity check, timeline, checklist, interest, evidence-pack ZIP (Section 5).
- **Phase 6, authentication:** signup (creates user, supplier and session together), login, logout, me. Argon2id password hashes (`argon2-cffi` 25.1.0), 10 to 128 characters, common passwords refused. 256-bit session tokens stored only as SHA-256, in an HttpOnly, SameSite=Lax cookie (Secure on https). Sessions expire after 7 idle days (sliding, refreshed at most hourly) or 30 days after login, and on logout. Login revokes any earlier session in the browser. Login and signup errors are generic, and an unknown email still costs one Argon2 check. Rate limits: login 5/min per IP+email and 20/hour per IP, signup 5/hour per IP, 300/min per user on other routes.
- **Phase 6.1, passwords and sessions:** forgot password (always the same 202 answer; email sent after the response), reset password (single-use, 15-minute token stored only as HMAC; consumed atomically with the password change; every session revoked; no automatic sign-in), change password (current password required; reuse of the current one refused; every session revoked and this browser given a new one), sign out everywhere. Confirmation emails after every change, with an honest `sent`/`failed` result. Email through `app/mail/`: a development file outbox (`STORAGE_DIR/outbox/*.eml`, `make email-outbox`) or SMTP.
- **Phase 7A, email verification:** new accounts start unverified (`users.email_verified_at` NULL) and receive a single-use link (`/verify-email#token=…`, 24 hours by default, HMAC-stored, consumed atomically, earlier links revoked on reissue). `POST /auth/verify-email` (token only, no session needed, verifies only the token's own user) and `POST /auth/resend-verification` (session, own address only, 1 per minute and 5 per hour, honest `sent`/`failed`). **Every case-workspace route requires a verified email** (403 `email_not_verified`, `VerifiedPrincipalDep`); account and recovery routes stay open. A completed password reset also verifies. Verification proves inbox control only, not business, Udyam or MSMED status.
- **Phase 6, authorisation:** one dependency resolves the cookie to `SupplierPrincipal(user_id, supplier_id)` on every supplier route. Services scope every query by that `supplier_id`, so another supplier's case, buyer, response, evidence file, download, timeline, interest, integrity check or pack answers 404, and writes leave the case untouched. Owner IDs in request bodies are rejected.

**Frontend (Next.js 16.4.3, React 19.3, Tailwind 4):**
- "Oxford Blue + Stone" design system (Geist), committed in `3175836`: landing page, dashboard, cases, Record delivery, case workspace (Overview with the DeemedClock timeline and the evidence pack, Evidence Vault, Buyer responses, Case Strength, Interest, Timeline).
- **Phase 6:** `/login` and `/signup` pages with field-level errors and loading states. A session guard on `/app/*` sends signed-out visitors to `/login?next=…`, and back afterwards (only `/app` paths are accepted). A session that ends mid-use leads to `/login?reason=expired` with an explanation. The sidebar and mobile menu show the user and business and a **Sign out** button.
- **Phase 6.1:** `/forgot-password` and `/reset-password` pages (the token is read from the URL fragment once, removed from the address bar and kept only in memory; missing, invalid and expired-link states). **Account settings** (`/app/settings`, new sidebar item): account details, Change password, and Sign out everywhere with a confirmation step. "Forgot password?" on the sign-in page.
- **Phase 7A:** unverified users see a "Confirm your email address" screen instead of any workspace page (sidebar: Confirm email, Settings, Sign out), with **Send a new link** and a live cooldown and an "I have confirmed my email" re-check. `/verify-email` confirms on a button click (link scanners cannot consume the token), with success, incomplete, and invalid-or-expired states. Account settings show Confirmed / Not confirmed with a resend card.
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
| POST | `/auth/verify-email` (120/hour per IP) | verification token in the body | always |
| POST | `/auth/resend-verification` (1/min, 5/hour per user) | session (unverified allowed) | always |
| GET | `/supplier` | session | not in production |
| GET, POST | `/buyers` | session, own buyers only | not in production |
| GET, POST | `/cases` | session, own cases only | not in production |
| GET | `/cases/{id}`, `/cases/{id}/checklist`, `/cases/{id}/interest?as_of=`, `/cases/{id}/timeline` | session, owner only (else 404) | not in production |
| GET, POST | `/cases/{id}/responses`; POST `/cases/{id}/responses/{rid}/remove-objection` | session, owner only | not in production |
| GET, POST | `/cases/{id}/evidence` (upload 15 MB, 30/min per user) | session, owner only | not in production |
| GET | `/evidence/{id}/download` | session, owner only | not in production |
| POST | `/cases/{id}/integrity-check` | session, owner only | not in production |
| GET | `/cases/{id}/evidence-pack` (5/hour per supplier and case) | session, owner only | not in production |

All supplier routes above also require a **verified email** (403 `email_not_verified`). All writes need `Origin` equal to `PUBLIC_BASE_URL` and `X-PaySetu-Client: web`. The supplier routes stay unmounted in production while the legal rules await review (DECISIONS.md Section 8).

## 6. Database and migrations

- Revisions: `bf48eb38df15` (baseline) → `7f9909eb7e4c` (demo case core) → `099b88746350` (accounts and ownership) → `d71bd50903a9` (password reset tokens, Phase 6.1) → **`5c2e8a41f0b7` (email verification, Phase 7A: `users.email_verified_at` added with `ALTER TABLE ADD COLUMN`, plus `email_verification_tokens`; every existing user stays unverified; no session revoked; no row changed)**. Accounts and ownership added `users`, `sessions`, `suppliers.owner_user_id` (nullable, unique; only a demo supplier may be unowned, enforced by triggers on SQLite and a CHECK on PostgreSQL).
- **Existing data:** the migration assigns no row to anyone. The seeded demo supplier stays unowned and unreachable until `DEMO_ACCOUNT_PASSWORD='…' make demo-account` gives it a login (default email `demo@paysetu.example`; refuses production; claims only an unowned demo supplier; the password is never printed).
- **Local database migrated (Phases 6, 6.1, 7A):** backed up before each migration (`paysetu.db.pre-phase6.bak`, `.pre-phase6_1.bak`, `.pre-phase7a.bak`; git-ignored). Before and after `5c2e8a41f0b7` the row counts were identical: 2 users, 1 session, 2 suppliers, 1 buyer, 3 cases, 3 evidence items, 16 timeline events, 2 responses. Both existing users are now **unverified**: sign in, use **Send a new link**, then `make email-outbox`.
- **How existing accounts complete verification:** sign in → confirmation screen → Send a new link → open the emailed link → Confirm my email. A completed password reset also confirms the email.

## 7. Test results (run 25 Oct 2026, final code)

| Check | Result |
| --- | --- |
| `make lint` (ruff check + format, eslint, prettier) | Pass |
| `make typecheck` (mypy strict on 87 files; tsc) | Pass |
| `make test` | **536 passed** (261 integration, 275 unit), 1 warning (Starlette notice about `httpx2`); domain coverage 100% line and branch (1,023 statements, 264 branches). Ran twice in a row: 536/536 both times |
| Phase 7A backend tests | `test_verification.py` (26 tests): signup creates an unverified user and a hash-only token, email uses `PUBLIC_BASE_URL` even with a forged Host; valid link opens the workspace in the same session; works signed out without signing in; invalid, used, expired (24 h boundary), configurable expiry, oversized; four concurrent verifications (exactly one wins); cross-account (B using A's link verifies only A); link dead after an address change; nothing granted beyond the flag; verify rate limit and CSRF; resend replaces links, 60 s cooldown and 5/hour, needs session, CSRF and an unverified email, ignores any email in the body; failed deliveries (signup and resend) reported honestly with links revoked and safe logs; unverified users keep account functions but every workspace operation answers 403 (walks the OpenAPI schema); password reset also verifies; existing accounts stay unverified across the migration; demo login unverified by default; existing user verifies by signing in and resending |
| Changed existing tests | The authorisation suite's second supplier now verifies its email first (otherwise 403 would hide the 404 ownership check), and `verify-email` joins its list of public routes; migration tests name the new head; the password log test now expects the signup verification email in its delivery list; the demo login in test helpers is created verified, as `DEMO_ACCOUNT_VERIFIED=1` does. No assertion was relaxed |
| Whole-app coverage (not gated) | 99%; `api/deps.py` 100%, `api/v1/auth.py` 99%, `services/auth.py` 96% |
| `make lint`, `make typecheck` (mypy strict on 95 files; tsc) | Pass |
| `make build` (Next.js) | Pass, including `/verify-email` |
| `alembic upgrade head` / `alembic check` / downgrade and upgrade | Pass |
| Playwright e2e (44 tests = 22 × 360×800 and 1280×800; real backend) | **44/44 passed with `--workers=2`, twice in a row** (1.1 min and 1.0 min). New `verification.spec.ts`: replaced link refused → new link → confirmed → dashboard; unverified user gets 403 from case APIs and the confirmation screen on workspace pages, settings still open; verified demo user records a delivery. The sign-up scenario in `auth.spec.ts` now goes signup → verification email → confirm → dashboard. Every other spec signs up and verifies through the emailed link |

**Bug found by e2e and fixed:** opening a second emailed link in a tab already on `/verify-email` changes only the URL fragment, so the page kept the old state and left the token in the address bar. The page now listens for `hashchange`; the same fix was applied to `/reset-password`.

**Not covered by e2e:** a real 24-hour expiry in the browser (the backend tests it with a frozen clock; e2e uses a replaced link, which shows the same "can no longer be used" state).

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
DEMO_ACCOUNT_PASSWORD='…' DEMO_ACCOUNT_VERIFIED=1 make demo-account   # demo login created verified (local only)
```

Local email testing (forgot and reset password): README.md, "Local email testing".

`make e2e` starts its own backend on :8100 (fresh database, `AUTH_SIGNUP_LIMIT_PER_HOUR=200`, a demo account with a test-only password) and Next on :3100 (`.next-e2e`). On a busy machine run `cd frontend && npx playwright test --workers=2`.

## 9. Security limitations (do not claim production-ready)

- **Production is not supported yet.** The supplier routes are unmounted in production, the legal rules are unreviewed, and the evidence pack is labelled an evaluation export.
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

- E2E timing on a loaded host with 4 workers (Section 7). Options: run e2e against `next build && next start` instead of `next dev`, or default to 2 workers.
- React development mode runs effects twice, so every page fetch is doubled in dev (not in production builds).
- Case references and timeline sequence numbers use read-then-insert with a bounded retry; replace with database sequences before multi-process deployment.
- Frontend copy is partly inline (AGENTS.md Section 4); no upload progress bar.
- Coverage gate covers only `app/domain`.

## 13. Recommended next tasks (priority order)

1. **Owner review and commit** of Phase 7A in the groups in Section 2.
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
