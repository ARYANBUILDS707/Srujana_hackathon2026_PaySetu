# PaySetu: Project Handover

Snapshot taken 25 Oct 2026, after Phase 6 (authentication and case-level authorisation). Verified against the workspace, not from memory. The previous handover's findings were audited in `docs/AUDIT_REPORT.md` (Section 9 records what was resolved).

## 1. Project overview

PaySetu helps Indian micro and small suppliers (Udyam-registered) keep provable evidence of a delivery and track the MSMED Act payment clock: acceptance date, due date, interest and a readiness checklist. It prepares and organises evidence; it is not a law firm, does not file claims and does not predict outcomes.

Source requirements: `docs/PRD.md`. Architecture: `docs/ARCHITECTURE.md`. Schema: `docs/DATABASE.md`. API contract: `docs/API.md`. Plan: `docs/IMPLEMENTATION_PLAN.md`. Decisions and legal review items: `docs/DECISIONS.md` (Phase 6 decisions: Section 8). Coding rules: `AGENTS.md`.

## 2. Git state

- Branch `backend`. Latest commit: `3175836 feat: complete PaySetu frontend redesign` (the redesign is committed).
- **Phase 6 is not committed.** `git status`: 41 modified and 17 untracked entries (the untracked ones include `docs/AUDIT_REPORT.md`, the new migration, the auth modules and tests, and the `(auth)` and `lib/session` folders). Nothing has been pushed.
- Suggested commit grouping for the owner: (1) audit report and documentation fixes (DESIGN, README, AUDIT_REPORT); (2) backend auth: migration, models, security, services, routes, tests, `requirements.txt`, `.env.example`, Makefile; (3) frontend auth: session provider, login and signup, shell, accessibility token fix, e2e; (4) remaining docs (HANDOVER, DECISIONS, API, ARCHITECTURE, DATABASE, IMPLEMENTATION_PLAN).

## 3. Completed features

**Backend (FastAPI 0.162, SQLite, SQLAlchemy 2.1.6, Alembic 1.20.1):**
- Platform: typed settings with a production gate, database and migrations, problem+json errors, request IDs, redacting JSON logs, injectable clock, body limit, CSRF, security headers, in-memory rate limits.
- Supplier routes: buyers, cases, buyer responses, evidence upload and download, integrity check, timeline, checklist, interest, evidence-pack ZIP (Section 5).
- **Phase 6, authentication:** signup (creates user, supplier and session together), login, logout, me. Argon2id password hashes (`argon2-cffi` 25.1.0), 10 to 128 characters, common passwords refused. 256-bit session tokens stored only as SHA-256, in an HttpOnly, SameSite=Lax cookie (Secure on https). Sessions expire after 7 idle days (sliding, refreshed at most hourly) or 30 days after login, and on logout. Login revokes any earlier session in the browser. Login and signup errors are generic, and an unknown email still costs one Argon2 check. Rate limits: login 5/min per IP+email and 20/hour per IP, signup 5/hour per IP, 300/min per user on other routes.
- **Phase 6, authorisation:** one dependency resolves the cookie to `SupplierPrincipal(user_id, supplier_id)` on every supplier route. Services scope every query by that `supplier_id`, so another supplier's case, buyer, response, evidence file, download, timeline, interest, integrity check or pack answers 404, and writes leave the case untouched. Owner IDs in request bodies are rejected.

**Frontend (Next.js 16.4.3, React 19.3, Tailwind 4):**
- "Oxford Blue + Stone" design system (Geist), committed in `3175836`: landing page, dashboard, cases, Record delivery, case workspace (Overview with the DeemedClock timeline and the evidence pack, Evidence Vault, Buyer responses, Case Strength, Interest, Timeline).
- **Phase 6:** `/login` and `/signup` pages with field-level errors and loading states. A session guard on `/app/*` sends signed-out visitors to `/login?next=…`, and back afterwards (only `/app` paths are accepted). A session that ends mid-use leads to `/login?reason=expired` with an explanation. The sidebar and mobile menu show the user and business and a **Sign out** button.
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

- Revisions: `bf48eb38df15` (baseline) → `7f9909eb7e4c` (demo case core) → **`099b88746350` (accounts and ownership)**: `users`, `sessions`, `suppliers.owner_user_id` (nullable, unique; only a demo supplier may be unowned, enforced by triggers on SQLite and a CHECK on PostgreSQL).
- **Existing data:** the migration assigns no row to anyone. The seeded demo supplier stays unowned and unreachable until `DEMO_ACCOUNT_PASSWORD='…' make demo-account` gives it a login (default email `demo@paysetu.example`; refuses production; claims only an unowned demo supplier; the password is never printed).
- **Local database migrated this session:** `backend/storage/paysetu.db` was backed up to `backend/storage/paysetu.db.pre-phase6.bak` (git-ignored), then upgraded. Row counts were identical before and after (1 supplier, 1 buyer, 3 cases, 3 evidence items, 16 timeline events, 2 responses, 1 bank rate). It has 0 users and the demo supplier is unowned. Run `make demo-account` to see that data in the app.

## 7. Test results (run 25 Oct 2026, final code)

| Check | Result |
| --- | --- |
| `make lint` (ruff check + format, eslint, prettier) | Pass |
| `make typecheck` (mypy strict on 87 files; tsc) | Pass |
| `make test` | **477 passed** (203 integration, 274 unit), 1 warning (Starlette notice about `httpx2`); domain coverage 100% line and branch (1,023 statements, 264 branches) |
| Phase 6 backend tests | `test_auth.py` (34 tests: signup, validation, duplicates, login, generic errors, inactive users, rate limits, CSRF, logs, me, logout, forged cookies, idle and absolute expiry, sliding, Secure cookies on https, production mounting, demo account, concurrent signup), `test_authorisation.py` (16 tests: every documented operation needs a session; 9 routes, including the integrity check, plus 4 more write attempts answer 404 across suppliers and change nothing; owner IDs in bodies rejected; per-supplier numbering; logout stops access), 2 migration tests (data preserved and unassigned; only demo suppliers may be unowned), 2 config tests |
| Whole-app coverage (not gated) | 99% overall; `services/auth.py` 98% (password-rehash branch untested); `services/pack.py` 88% |
| `make build` (Next.js) | Pass; 13 routes including `/login` and `/signup` |
| `alembic upgrade head` / `alembic check` / downgrade and upgrade | Pass; models and schema agree |
| Playwright e2e (30 tests = 15 × 360×800 and 1280×800; real backend; each test signs up its own account) | **30/30 passed with `--workers=2`.** With the default 4 workers, four full runs after the auth tests were in place had timing failures in 6, 2, 1 and 1 tests (a different test each time). Traces show the API responding in about 2 s or less; the failures came from the Next.js **dev** server compiling routes on first use (up to 3.8 s) while the host was heavily loaded (load average 11 to 50, including a running `make dev` with `--reload` and the macOS malware scanner) |

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
```

`make e2e` starts its own backend on :8100 (fresh database, `AUTH_SIGNUP_LIMIT_PER_HOUR=200`, a demo account with a test-only password) and Next on :3100 (`.next-e2e`). On a busy machine run `cd frontend && npx playwright test --workers=2`.

## 9. Security limitations (do not claim production-ready)

- **Production is not supported yet.** The supplier routes are unmounted in production, the legal rules are unreviewed, and the evidence pack is labelled an evaluation export.
- **No password change, reset or account deletion.** A user who forgets a password cannot recover the account. A compromised session ends only by logout or expiry (no "sign out everywhere").
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

1. **Owner review and commit** of Phase 6 in the groups in Section 2.
2. **Auth completion:** password change (revoke other sessions), password reset with SMTP (P1), "sign out everywhere", account deletion request; record `actor_id` on new timeline events.
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
