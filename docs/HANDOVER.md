# PaySetu: Project Handover

Snapshot taken 25 Oct 2026, end of session. Verified against the workspace (not from memory).

## 1. Project overview

PaySetu helps Indian micro and small suppliers (Udyam-registered) keep provable evidence of a delivery and track the MSMED Act payment clock: acceptance date, due date, interest and a readiness checklist. It prepares and organises evidence; it is not a law firm, does not file claims and does not predict outcomes.

Source requirements: `docs/PRD.md`. Architecture: `docs/ARCHITECTURE.md`. Schema: `docs/DATABASE.md`. API contract: `docs/API.md`. Plan: `docs/IMPLEMENTATION_PLAN.md`. Decisions and legal review items: `docs/DECISIONS.md`. Coding rules: `AGENTS.md`.

## 2. Git state

- Branch: `backend`. Last commit: `8f85916 feat(backend): implement evaluation demo APIs`.
- **Nothing since that commit is committed.** `git status` shows 23 modified files and 14 untracked entries (some are directories): the evidence-pack export, the frontend demo workspace, the blue-and-white design update, the handover files, and several config changes. Nothing has been pushed.
- Suggested commit grouping for the owner: (1) evidence pack backend and tests, (2) frontend demo workspace and e2e, (3) design system and docs, (4) config and tooling.

## 3. Completed features

**Backend (FastAPI, SQLite, SQLAlchemy 2.1, Alembic):**
- Typed settings with a production gate for simulated adapters (T1.1).
- Database engine, sessions, SQLite pragmas and migrations (T1.2): baseline `bf48eb38df15`, demo schema `7f9909eb7e4c`.
- Error framework, `application/problem+json`, request IDs, structured JSON logs with redaction (T1.3).
- Injectable clock: UTC instants, Asia/Kolkata legal date (T1.4).
- Security middleware: body size cap, CSRF on unsafe `/api/` methods, security headers, rate limits (T1.5).
- Demo vertical slice: cases, buyers, buyer responses, evidence upload and download, integrity check, timeline, checklist, interest (see §5).
- Evidence Pack export (see §6).

**Frontend (Next.js 16.4.3, React 19, Tailwind 4):**
- Landing page, dashboard, case list, New delivery, and per-case tabs: Overview, Evidence, Buyer responses, Case Strength, Interest, Timeline.
- Blue-and-white design tokens; contrast ratios checked against WCAG AA (recorded in `docs/DESIGN.md` §2).
- Typed API client generated from the backend OpenAPI schema (`make api-types`).

**Domain engine (pure Python, `backend/app/domain/`, 100% line and branch coverage):** rules loader and validator, DeemedClock, interest engine, eligibility, integrity (SHA-256 and hash chain), checklist C01–C17, next-action rules.

## 4. Status of the five core modules

| PRD module | Status | Notes |
| --- | --- | --- |
| **DeemedClock** | Implemented in domain and API; in UI | Computed on every read. Only written objections change acceptance. Legal readings are provisional (see §10). |
| **Evidence Vault** | Partly implemented | Upload, SHA-256, download, append-only timeline with DB triggers, integrity check. Missing: `.eml` DKIM grading, RFC 3161 timestamps, exclusion UI and endpoint (DB exclusion path exists but no route). |
| **Case Strength** | Implemented in domain, API and UI | Checklist C01–C17. Letters and payments are not built, so C11 and C13 always show missing. |
| **Buyer Cost Page** | Not built | Only the interest figure exists. No share links, no `/b/[token]` page. |
| **Sealed Pack** | Partly implemented | On-demand ZIP export only; no stored or versioned packs, no PDF, no s.63 draft, no advocate link. |

## 5. Current API endpoints (`/api/v1`, demo build)

Mounted only when `APP_ENV` is not `production`. No authentication: one synthetic demo supplier.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness (always mounted) |
| GET | `/supplier` | Demo supplier with eligibility |
| GET, POST | `/buyers` | List and create buyers |
| GET, POST | `/cases` | List and create cases (reference allocated, DeemedClock validated) |
| GET | `/cases/{id}` | Case with clock, amounts, checklist summary, next action |
| GET | `/cases/{id}/checklist` | Case Strength C01–C17 |
| GET | `/cases/{id}/interest?as_of=` | Illustrative interest from the engine |
| GET, POST | `/cases/{id}/responses` | List and record buyer responses |
| POST | `/cases/{id}/responses/{rid}/remove-objection` | Mark an objection removed |
| GET, POST | `/cases/{id}/evidence` | List evidence; upload (multipart, 15 MB cap) |
| GET | `/evidence/{id}/download` | Original file bytes |
| POST | `/cases/{id}/integrity-check` | Verify files and chain; records an event |
| GET | `/cases/{id}/timeline` | Hash-chained events |
| GET | `/cases/{id}/evidence-pack` | Evidence ZIP (read-only, see §6) |

Writes require `Origin` equal to `PUBLIC_BASE_URL` and header `X-PaySetu-Client: web`.

## 6. Evidence Pack export (current implementation and limits)

- **Code:** `backend/app/services/pack.py` (verification, data gathering, read-only check), `backend/app/documents/pack.py` (pure builder), route in `backend/app/api/v1/demo_cases.py`, UI in `frontend/src/components/cases/EvidencePackCard.tsx`.
- **Behaviour:** verifies every stored file and the timeline chain; refuses with 409 `integrity_failed` if anything fails, or if a file changes while the pack is built. Writes nothing to the database. The same `verify_case` logic serves `check_integrity`.
- **Contents:** README (with verification steps), case summary, DeemedClock and interest with rules relied on, timeline (Markdown and JSON), checklist, verification report, original evidence files, `manifest.json` with SHA-256 of every other file. The pack ID is the SHA-256 of `manifest.json`, returned in the `X-PaySetu-Pack-SHA256` header.
- **Limits:** Markdown and JSON only (no PDF). Not stored or versioned; no `sealed_packs` table; no timeline event for an export. No Section 63 certificate (no counsel-reviewed template; LR-16). No counsel-questions file, no supplier-documents folder, no advocate sharing. Export rate limit 5 per hour per case.
- **Tests:** `backend/tests/integration/test_evidence_pack.py` (contents, byte-for-byte evidence, manifest consistency, read-only and repeatable, tamper and missing-file refusal, unknown case, rate limit, hostile filenames, no secrets or paths, production unmounted); `frontend/tests/e2e/evidence-pack.spec.ts` (browser download, independent manifest check, tamper refusal).

## 7. Test results and coverage (verified this session)

| Check | Result |
| --- | --- |
| `pytest` (backend) | 423 passed, 1 warning (Starlette notice about `httpx2`) |
| Domain coverage (`app/domain`) | 100% line, 100% branch (1,023 statements, 264 branches), enforced by `make test` |
| `mypy --strict` (app, tests, alembic, seed, tools) | Pass, 75 files |
| `ruff check` / `ruff format --check` | Pass |
| Frontend `eslint`, `prettier --check`, `tsc` | Pass (last run; `tsconfig.json` was re-formatted to match the repo's Prettier config) |
| `next build` | Pass |
| Playwright e2e | 16 passed (8 tests × 360×800 and 1280×800), zero server errors in the log |

Non-domain coverage is not gated. Measured this session (`pytest --cov --cov-branch`): `api/v1/demo_cases.py` 100%; `services/cases.py` 99% (one line uncovered); `documents/pack.py` 99%; `services/pack.py` 88% (uncovered lines 82, 96, 99–101; not yet analysed). Whole `app/` is 99% line and branch.

## 8. Commands

```bash
make setup                 # backend venv + pip; frontend npm ci + Playwright Chromium
cp backend/.env.example backend/.env   # then set real local values (never commit)
make migrate               # alembic upgrade head
make seed                  # synthetic demo supplier, sample buyer, unverified bank rate
make dev                   # API :8000 + web :3000 (open http://localhost:3000)
make lint | make typecheck | make test | make build | make e2e
make api-types             # regenerate frontend types after any API change
```

Requirements: Python 3.12, Node 22 (`.nvmrc`). `make e2e` starts its own backend on :8100 and Next on :3100, with a separate build folder (`.next-e2e`), so it does not disturb `make dev`.

## 9. Demo-mode limitations

- **No login.** One synthetic supplier; all data is shared by everyone who can reach the server. Local use only. The demo router is mounted only when `APP_ENV` is not `production`, and the app refuses to start in production with simulated adapters unless explicitly overridden.
- **Synthetic data only.** Seeded names, buyers and emails are samples (`.invalid` domains). Do not enter real business or personal data.
- **Letters not built.** Delivery intimation and demand are not drafted, so checklist items C11 and C13 always show missing and the next-step copy tells the user to send them and keep proof.
- **Payments not built.** Paid amount is always zero.
- **Bank rate unverified.** Only 5.75% from 7 Oct 2026 is recorded (from the ideation document). Earlier periods return "rate data unavailable"; nothing is invented.
- **Single process.** Rate limits and the evidence-pack `case_id` limiter are in-memory.
- **Demo build flags.** Responses carry `demo_mode: true`; the UI shows a demo banner.

## 10. Known issues and technical debt

- **Concurrency:** case references and timeline sequence numbers are allocated by read-then-insert and protected by a bounded retry (`_retry_allocation_conflict`). Adequate for one process; replace with database sequences before any multi-process deployment.
- **Frontend copy:** form labels and some one-line messages are still inline in page files, not in `src/content/`, contrary to AGENTS.md §4.
- **No upload progress bar** (DESIGN.md §5.3 asks for one).
- **Coverage gate covers only `app/domain`.** Services, API and documents are tested but not coverage-gated.
- **Migration caveat:** SQLite batch rebuilds with foreign keys on may need care in future migrations (see DATABASE.md §8).
- **Naming:** `app/errors.py` classes deliberately break Ruff N818 (waived per-file).
- **Config drift to watch:** `backend/requirements.txt` pins runtime packages only; dev packages are in `requirements-dev.txt`, and `openapi-typescript` is a frontend dev dependency.
- **Stale README sections:** the "Current implementation status" table in the root README is partly out of date (it still lists the database as not started in places); recheck before publishing.
- **Git hygiene:** a large uncommitted change set spans backend, frontend and docs (see §2).

## 11. Pending legal review

Advocate review is required before any non-demo use. Full register: `docs/DECISIONS.md` §3 (LR-01 to LR-25). Key items affecting computed output:

- **LR-01 to LR-07:** day counting (Day 15 window end, Day 16 appointed day), no holiday adjustment, late objections, what counts as writing, acknowledgements, several objections, 45-day cap.
- **LR-12 to LR-14:** interest mechanics, bank-rate selection and principal-first payment allocation. Owner-approved as **provisional simulation defaults only**; not validated law.
- **LR-16:** Section 63 certificate. No template; none generated.
- **LR-21 to LR-25:** MSMED (Amendment) Act 2026 (Act 16 of 2026). Reviewed from the Bill text and PIB summary: ss.2(b), 15, 16 and 17 are not amended. Enacted text and S.O. 5575(E) still need Gazette confirmation.

The rule set `msmed-v1` is in `backend/app/rules/msmed-v1.toml`. Every output lists its unconfirmed rules.

## 12. Recommended next tasks (priority order)

1. **Commit the current work in logical groups** (§2), after reviewing the diff. Owner action.
2. **Harden the demo for evaluation:** re-measure coverage of services and documents; move remaining frontend copy into `src/content/`; add the upload progress bar.
3. **Sealed Pack persistence (Phase 10):** `sealed_packs` table (append-only), versioned packs, `pack_generated` event, PDF output via ReportLab, `00_READ_ME` wording reviewed.
4. **Buyers and letters (Phases 4 and 9):** buyer edit endpoint; intimation and demand drafting with approve-then-send (send simulated); fixes C11 and C13.
5. **Auth (Phase 3):** users, sessions, `SupplierPrincipal`; replaces the demo supplier and removes `is_demo` routing.
6. **Legal:** advocate review of LR items; decide whether an s.63 template is commissioned.
7. **Share links and Buyer Cost Page (Phase 10):** only after auth and reviewed templates.

## 13. Resume checklist for the next session

1. `git status` and commit or stash deliberately (do not commit unreviewed generated files).
2. Run `make test` and `make e2e`; both should pass as of this handover.
3. Read `docs/IMPLEMENTATION_PLAN.md` for the phase in progress; this handover supersedes its "current status" lines only where marked above.
