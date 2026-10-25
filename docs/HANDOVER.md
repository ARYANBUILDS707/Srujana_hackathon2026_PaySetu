# PaySetu: Project Handover

Snapshot taken 25 Oct 2026, after Phase 6.1 (password reset, password change and session management), on top of Phase 6 (authentication and case-level authorisation). Verified against the workspace, not from memory. The previous handover's findings were audited in `docs/AUDIT_REPORT.md` (Section 9 records what was resolved).

## 1. Project overview

PaySetu helps Indian micro and small suppliers (Udyam-registered) keep provable evidence of a delivery and track the MSMED Act payment clock: acceptance date, due date, interest and a readiness checklist. It prepares and organises evidence; it is not a law firm, does not file claims and does not predict outcomes.

Source requirements: `docs/PRD.md`. Architecture: `docs/ARCHITECTURE.md`. Schema: `docs/DATABASE.md`. API contract: `docs/API.md`. Plan: `docs/IMPLEMENTATION_PLAN.md`. Decisions and legal review items: `docs/DECISIONS.md` (Phase 6 decisions: Section 8; Phase 6.1: Section 9). Coding rules: `AGENTS.md`.

## 2. Git state

- Branch `backend`. Latest commit: `665a6ab feat: implement secure authentication and case authorisation` (Phase 6, committed by the owner).
- **Phase 6.1 is not committed.** `git status`: 30 modified and 8 untracked entries (new: the `d71bd50903a9` migration, `backend/app/mail/`, `backend/tools/outbox.py`, `test_passwords.py`, the forgot-password, reset-password and settings pages, `passwords.spec.ts`). Nothing has been pushed.
- Suggested commit grouping: (1) backend: migration, mail package, auth service and routes, rate limits, log fields, tests, `.env.example`, Makefile, `tools/outbox.py`; (2) frontend: pages, settings, session context, nav, e2e; (3) docs.

## 3. Completed features

**Backend (FastAPI 0.162, SQLite, SQLAlchemy 2.1.6, Alembic 1.20.1):**
- Platform: typed settings with a production gate, database and migrations, problem+json errors, request IDs, redacting JSON logs, injectable clock, body limit, CSRF, security headers, in-memory rate limits.
- Supplier routes: buyers, cases, buyer responses, evidence upload and download, integrity check, timeline, checklist, interest, evidence-pack ZIP (Section 5).
- **Phase 6, authentication:** signup (creates user, supplier and session together), login, logout, me. Argon2id password hashes (`argon2-cffi` 25.1.0), 10 to 128 characters, common passwords refused. 256-bit session tokens stored only as SHA-256, in an HttpOnly, SameSite=Lax cookie (Secure on https). Sessions expire after 7 idle days (sliding, refreshed at most hourly) or 30 days after login, and on logout. Login revokes any earlier session in the browser. Login and signup errors are generic, and an unknown email still costs one Argon2 check. Rate limits: login 5/min per IP+email and 20/hour per IP, signup 5/hour per IP, 300/min per user on other routes.
- **Phase 6.1, passwords and sessions:** forgot password (always the same 202 answer; email sent after the response), reset password (single-use, 15-minute token stored only as HMAC; consumed atomically with the password change; every session revoked; no automatic sign-in), change password (current password required; reuse of the current one refused; every session revoked and this browser given a new one), sign out everywhere. Confirmation emails after every change, with an honest `sent`/`failed` result. Email through `app/mail/`: a development file outbox (`STORAGE_DIR/outbox/*.eml`, `make email-outbox`) or SMTP.
- **Phase 6, authorisation:** one dependency resolves the cookie to `SupplierPrincipal(user_id, supplier_id)` on every supplier route. Services scope every query by that `supplier_id`, so another supplier's case, buyer, response, evidence file, download, timeline, interest, integrity check or pack answers 404, and writes leave the case untouched. Owner IDs in request bodies are rejected.

**Frontend (Next.js 16.4.3, React 19.3, Tailwind 4):**
- "Oxford Blue + Stone" design system (Geist), committed in `3175836`: landing page, dashboard, cases, Record delivery, case workspace (Overview with the DeemedClock timeline and the evidence pack, Evidence Vault, Buyer responses, Case Strength, Interest, Timeline).
- **Phase 6:** `/login` and `/signup` pages with field-level errors and loading states. A session guard on `/app/*` sends signed-out visitors to `/login?next=…`, and back afterwards (only `/app` paths are accepted). A session that ends mid-use leads to `/login?reason=expired` with an explanation. The sidebar and mobile menu show the user and business and a **Sign out** button.
- **Phase 6.1:** `/forgot-password` and `/reset-password` pages (the token is read from the URL fragment once, removed from the address bar and kept only in memory; missing, invalid and expired-link states). **Account settings** (`/app/settings`, new sidebar item): account details, Change password, and Sign out everywhere with a confirmation step. "Forgot password?" on the sign-in page.
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
| GET | `/supplier` | session | not in production |
| GET, POST | `/buyers` | session, own buyers only | not in production |
| GET, POST | `/cases` | session, own cases only | not in production |
| GET | `/cases/{id}`, `/cases/{id}/checklist`, `/cases/{id}/interest?as_of=`, `/cases/{id}/timeline` | session, owner only (else 404) | not in production |
| GET, POST | `/cases/{id}/responses`; POST `/cases/{id}/responses/{rid}/remove-objection` | session, owner only | not in production |
| GET, POST | `/cases/{id}/evidence` (upload 15 MB, 30/min per user) | session, owner only | not in production |
| GET | `/evidence/{id}/download` | session, owner only | not in production |
| POST | `/cases/{id}/integrity-check` | session, owner only | not in production |
| GET | `/cases/{id}/evidence-pack` (5/hour per supplier and case) | session, owner only | not in production |

All writes need `Origin` equal to `PUBLIC_BASE_URL` and `X-PaySetu-Client: web`. The supplier routes stay unmounted in production while the legal rules await review (DECISIONS.md Section 8).

## 6. Database and migrations

- Revisions: `bf48eb38df15` (baseline) → `7f9909eb7e4c` (demo case core) → `099b88746350` (accounts and ownership) → **`d71bd50903a9` (password reset tokens, Phase 6.1; creates one table, changes no row)**. Accounts and ownership added `users`, `sessions`, `suppliers.owner_user_id` (nullable, unique; only a demo supplier may be unowned, enforced by triggers on SQLite and a CHECK on PostgreSQL).
- **Existing data:** the migration assigns no row to anyone. The seeded demo supplier stays unowned and unreachable until `DEMO_ACCOUNT_PASSWORD='…' make demo-account` gives it a login (default email `demo@paysetu.example`; refuses production; claims only an unowned demo supplier; the password is never printed).
- **Local database migrated (both phases):** `backend/storage/paysetu.db` was backed up before each migration (`paysetu.db.pre-phase6.bak`, `paysetu.db.pre-phase6_1.bak`, git-ignored). Before and after `d71bd50903a9` the row counts were identical: 2 users, 1 session, 2 suppliers, 1 buyer, 3 cases, 3 evidence items, 16 timeline events, 2 responses.

## 7. Test results (run 25 Oct 2026, final code)

| Check | Result |
| --- | --- |
| `make lint` (ruff check + format, eslint, prettier) | Pass |
| `make typecheck` (mypy strict on 87 files; tsc) | Pass |
| `make test` | **509 passed** (235 integration, 274 unit), 1 warning (Starlette notice about `httpx2`); domain coverage 100% line and branch (1,023 statements, 264 branches). Ran 3 times in a row after the outbox-ordering fix below: 509/509 each time |
| Phase 6.1 backend tests | `test_passwords.py` (32 tests): reset email with a hash-only token and private outbox files; identical answers for known, unknown and inactive emails; earlier tokens revoked; rate limits (forgot, reset, change); CSRF; full reset flow (password changed, all sessions revoked, no sign-in, notice sent); reused, expired (15 min boundary), invalid and oversized tokens; policy failures that do not consume the token; four concurrent resets with one token (exactly one wins); cross-account isolation; failed reset email (same answer, token revoked, safe log line); failed notice reported as `failed`; SMTP sender with a fake server (settings used, failure mapped); production outbox withholds bodies; change password (new session here, others revoked, old cookie dead, outstanding links revoked; wrong current, reuse, weak, no session, no CSRF); sign out everywhere (every device, other users untouched, old cookie dead); no token, password or address in logs |
| Phase 6 backend tests | `test_auth.py` (34), `test_authorisation.py` (16, now listing forgot and reset as the only new public routes), migration and config tests: all still pass |
| Whole-app coverage (not gated) | 99%; `api/v1/auth.py` 100%, `mail/` 98 to 100%, `services/auth.py` 97% |
| `make lint`, `make typecheck` (mypy strict on 92 files; tsc) | Pass |
| `make build` (Next.js) | Pass, including `/forgot-password`, `/reset-password` and `/app/settings` |
| `alembic upgrade head` / `alembic check` / downgrade and upgrade | Pass |
| Playwright e2e (38 tests = 19 × 360×800 and 1280×800; real backend) | **38/38 passed with `--workers=2`, in two consecutive runs** (57.8 s and 55.8 s). New `passwords.spec.ts`: forgot → reset with the link read from the development outbox → sign in with the new password, reused link refused; unknown email and broken links; change password in settings; sign out everywhere across two browser contexts. Not re-run with 4 workers this session: Phase 6 found that configuration times out on a loaded machine (dev-server compile time), see Section 12 |

**Flaky test found and fixed this session.** `test_a_new_request_revokes_the_previous_unused_token` failed in about half of the runs. Cause: outbox file names began with the injected clock's timestamp, which the tests freeze, so two messages sorted by a random suffix and the "newest" was picked at random. Fix: file names now include a nanosecond counter, so the outbox always sorts in send order (`app/mail/senders.py`). After the fix: 10/10 runs of the file and 3/3 full runs passed. No assertion was relaxed.

**Development-mode bug found by e2e and fixed.** The reset page read the token in an effect that React's development mode runs twice; the second run found the already-cleared fragment and showed "incomplete link". The token is now kept in a ref after the first read.

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
make email-outbox          # newest development emails, including reset links (refuses production)
```

Local email testing (forgot and reset password): README.md, "Local email testing".

`make e2e` starts its own backend on :8100 (fresh database, `AUTH_SIGNUP_LIMIT_PER_HOUR=200`, a demo account with a test-only password) and Next on :3100 (`.next-e2e`). On a busy machine run `cd frontend && npx playwright test --workers=2`.

## 9. Security limitations (do not claim production-ready)

- **Production is not supported yet.** The supplier routes are unmounted in production, the legal rules are unreviewed, and the evidence pack is labelled an evaluation export.
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

1. **Owner review and commit** of Phase 6.1 in the groups in Section 2.
2. **Auth completion:** account deletion request, email verification at signup, record `actor_id` on new timeline events; configure a real SMTP relay before any non-local use.
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
