# PaySetu: Session Audit Report

| Field | Value |
| --- | --- |
| Period covered | 25 Oct 2026, from the first documentation commit (`7d0fba7`, 01:20) to the frontend redesign commit (`3175836`, 15:49) |
| Branch | `backend` (working tree clean when this report was written) |
| Prepared by | Claude Code (AI coding assistant), from the conversation record and a re-check of the workspace |
| Purpose | Record what was built, how it was verified, what went wrong along the way, and what is still open |

All figures in Section 4 were re-measured for this report unless marked otherwise. Commits were made by the repository owner (`ARYANBUILDS707`); the assistant did not commit, push or switch branches.

---

## 1. Summary

In one working day the project went from documentation only to a working evaluation build:

- A full documentation set: PRD, design, architecture, database, API, agent rules, implementation plan and decision log.
- A pure-Python legal and evidence engine (M1). It has 100% line and branch coverage and is guarded by a coverage gate.
- A FastAPI backend with typed settings, a database, migrations, error handling, logging, an injectable clock and a security middleware stack.
- A demo vertical slice (cases, evidence, buyer responses, integrity checks, checklist, interest) and a downloadable evidence pack.
- A Next.js workspace on top of the real APIs, redesigned at the end of the day in the "Oxford Blue + Stone" theme.

Not done: authentication, letters, sharing, the Buyer Cost Page and advocate review of the legal readings.

## 2. Timeline of work

| # | Commit | Time | Work | Size |
| --- | --- | --- | --- | --- |
| 1 | `7d0fba7` | 01:20 | Docs: README, PRD, DESIGN, ARCHITECTURE, DATABASE, API, AGENTS, IMPLEMENTATION_PLAN | 9 files, +4,220 |
| 2 | `816e5cb` | 01:43 | Phase 0 foundation: repo layout, Makefile, lint/type/test tooling, Next.js and FastAPI skeletons, DECISIONS.md | 34 files, +7,586 |
| 3 | `164c2b3` | 02:23 | M1 domain engine: DeemedClock, interest engine, eligibility, hash-chained timeline, checklist C01–C17, next-action rules, rule set `msmed-v1.toml`, 24 counsel-readable fixtures | 34 files, +4,258 |
| 4 | `f8ad5e5` | 04:16 | T1.1 typed settings with a production gate for simulated adapters | 15 files, +503 |
| 5 | `bb4c5b4` | 04:24 | T1.2 SQLAlchemy engine (SQLite WAL, foreign keys, busy timeout) and Alembic baseline | 19 files, +634 |
| 6 | `f46312d` | 04:46 | T1.3/T1.4 problem+json errors, request IDs, redacting JSON logs, injectable clock | 9 files, +884 |
| 7 | `0760a3e` | 04:53 | T1.5 security middleware: body size cap, CSRF, security headers, rate limiter | 10 files, +678 |
| 8 | `8f85916` | 05:05 | Demo APIs: cases, buyers, evidence upload and download, responses, integrity, checklist, interest, timeline | 20 files, +2,611 |
| 9 | `02891c1` | 06:09 | Frontend demo workspace, blue-and-white design, evidence pack export, retry on allocation races, CLAUDE.md, HANDOVER.md | 66 files, +6,414 |
| 10 | `3175836` | 15:49 | Frontend redesign (Oxford Blue + Stone): shell, landing page, dashboard, case workspace, all case sections | 35 files, +1,329 / −508 |

## 3. What was built

### 3.1 Documentation and governance
- `AGENTS.md` (coding and security rules), `CLAUDE.md` (short entry point) and `docs/HANDOVER.md` (current state and next tasks).
- `docs/DECISIONS.md`:
  - ADRs.
  - Legal review items LR-01 to LR-25.
  - Logged deviations for M1, the demo slice, the frontend and the evidence pack.
- Simulation defaults D3–D5 are recorded as provisional. The MSMED 2026 amendment is flagged for review.

### 3.2 Domain engine (`backend/app/domain/`)
- Pure functions with no I/O. The DeemedClock is computed when read; no status is stored.
- Interest uses `Decimal` arithmetic with monthly rests.
- Rules come from the versioned `msmed-v1.toml`. Each rule has a tier (S statute, I interpretation, C configurable assumption) and a verification status.

### 3.3 Backend platform
- `create_app(settings, clock)` factory.
- Middleware order: request context, security headers, body limit, CSRF, rate limit.
- Data:
  - Two Alembic revisions: `bf48eb38df15` baseline and `7f9909eb7e4c` demo case core.
  - SQLite triggers make `timeline_events` and `evidence_items` append-only.
- Evidence store:
  - Content-addressed and write-once.
  - Files are saved with 0600 permissions.
  - File type is detected from magic bytes.
- Demo routes are mounted only outside production.
- The seed script refuses to run in production. The seeded bank rate (5.75%) is marked `verified=false`.

### 3.4 Evidence pack
- `GET /api/v1/demo/cases/{id}/evidence-pack` streams a ZIP containing:
  - README_FIRST
  - Case summary, clock and interest, timeline (Markdown and JSON), checklist, verification report
  - The original evidence files
  - `manifest.json` with a SHA-256 for every file
- The pack ID is the SHA-256 of the manifest.
- The export is refused (409) if any file or the timeline fails verification.
- The output is the same byte for byte for the same case and clock.
- Rate limit: 5 packs per hour per case.

### 3.5 Frontend
- Next.js 16.4.3, React 19.3 and Tailwind 4. The typed API client is generated from `/openapi.json`.
- Routes: landing, dashboard, cases, record delivery, and the case workspace (Overview, Evidence, Buyer responses, Case Strength, Interest, Timeline).
- The redesign (commit 10) added:
  - Semantic tokens only, with no raw hex in components.
  - Geist fonts.
  - A 240px sidebar and a 64px top bar with breadcrumbs, plus a collapsible mobile menu.
  - A chronological DeemedClock timeline labelled "Recorded fact", "Calculated by PaySetu" or "Pending". It has "Why this date?" explanations and flags rules that are not yet reviewed.
  - A drag-and-drop upload zone that rejects files over 15 MB in the browser before upload.
  - A per-file integrity status after a check.
  - A Case Strength progress bar.
- No backend file was changed in the redesign.

## 4. Verification evidence

| Check | Command | Result | When |
| --- | --- | --- | --- |
| Backend lint | `make lint` (ruff check and format) | All checks passed | Re-run for this report |
| Frontend lint | `make lint` (eslint, prettier) | Passed, all files formatted | Re-run for this report |
| Typecheck | `make typecheck` (mypy strict, tsc) | Passed | Re-run for this report |
| Backend tests | `make test` | **423 passed**, 1 warning (Starlette `httpx` deprecation in a dependency) | Re-run for this report |
| Domain coverage gate | `make test` | 1,023 statements, 264 branches, **100%** | Re-run for this report |
| Whole-app coverage (not gated) | `pytest --cov=app` | 99% overall. `services/pack.py` 88% (lines 82, 96, 99–101 uncovered); `documents/pack.py` 99% (line 133) | Re-run for this report |
| Production build | `npm run build` | Passed, 11 routes | Last run during the redesign, not re-run |
| End-to-end | `npm run e2e` (Playwright, real backend, 360px and 1280px) | **16 passed** on the final run. The first run had 1 failure (see 5.2) | Last run during the redesign, not re-run |
| Horizontal overflow | Temporary Playwright script, 10 screens × 5 widths (360/390/768/1280/1440) | No overflow found; the script was deleted afterwards | During the redesign |

## 5. Incidents and how they were resolved

### 5.1 Defects found and fixed during the work

| Issue | Fix |
| --- | --- |
| `python-multipart` missing, so uploads failed | Installed it and pinned it in `backend/requirements.txt` |
| Autogenerated migration had unused imports | Hand-reviewed; SQLite triggers added; deviation logged |
| Two requests could get the same case reference or timeline sequence (`PS-2026-0001` returned a 500) | Bounded retry (5 attempts) on allocation conflicts. The file is stored before the retryable database step. Deterministic race tests added |
| Migration tests still asserted "no business tables" | Rewritten to check the demo table set and that the schema matches the models |
| Next.js prerender and Cache Components warnings | Cache Components disabled |
| A stale `next-server` held port 3000 and blocked Playwright | Found with `ps`/`lsof` before killing anything. E2E now builds into its own `.next-e2e` folder |
| Prettier reformatted `tsconfig.json` | Restored from git |
| The handover first contained an invented explanation of coverage and a technical-debt item that had not been checked | Both were removed before handover. The handover now lists the uncovered lines and says they are not analysed |

### 5.2 Test changes
- One e2e test was changed: in `smoke.spec.ts`, the link name "Open the demo workspace" became "Open demo workspace" to match the new copy. No assertion was removed or loosened.
- The first full e2e run of the redesign had one failure: mobile-360, "supplier logs a delivery…", where the `timeline-list` was not found after the Timeline tab was clicked. It did not reproduce in 3 repeats or in two later full runs. The cause was not found, so treat it as a possible flake in the horizontally scrolling case tab bar on small screens.

## 6. Open findings

| # | Severity | Finding | Location |
| --- | --- | --- | --- |
| F1 | High (product) | No authentication. The workspace runs as a single demo supplier, so case-level authorisation does not exist yet | Whole app |
| F2 | High (legal) | LR-01 to LR-25 are still waiting for advocate review. Every date and amount is labelled illustrative | `docs/DECISIONS.md` §3 |
| F3 | Medium | Contrast ratios in `docs/DESIGN.md` §2.1 are for the old palette and have not been re-measured for the new tokens. `ink-faint` (#69747B) is about 4.3:1 on `canvas`, below AA, so it is used on white only | `docs/DESIGN.md` §2 |
| F4 | Low | `docs/DESIGN.md` is inconsistent. The new palette note says "26 Oct 2026" but the change was made on 25 Oct 2026 (an error by the assistant). The status line still says blue-and-white. §3 typography and the PDF section still name IBM Plex | `docs/DESIGN.md` lines 5, 64, 86–88, 508 |
| F5 | Low | `docs/HANDOVER.md` is stale. It says the work is uncommitted (it is now committed) and describes the blue-and-white design | `docs/HANDOVER.md` lines 14, 30 |
| F6 | Low | `README.md` status mentions IBM Plex and blue-and-white, and says "no packs" although the pack export exists | `README.md` lines 337, 404 |
| F7 | Low | Pack service coverage is 88%; four code paths are untested | `backend/app/services/pack.py` |
| F8 | Low | The rate limiter is in memory, so limits reset on restart and are not shared across processes | `backend/app/security/rate_limit.py` |
| F9 | Info | Known UI limits caused by the API: no checklist category field, no "last updated" on cases, integrity is checked per case (not per file), and there is no supporting-evidence link on buyer responses | Frontend |
| F10 | Info | One e2e flake was seen once on mobile-360 (see 5.2) | `tests/e2e/demo-journey.spec.ts` |

## 7. Process compliance

| Rule | Status |
| --- | --- |
| No commit, push or branch switch by the assistant | Met. All 10 commits are by the owner |
| Run lint, typecheck and test before reporting done | Met at each stage. Re-confirmed for this report |
| Domain coverage stays at 100% with no exclusions | Met |
| Tests not weakened | Met. One copy string updated (5.2) |
| No invented legal readings, bank rates or certifications | Met. The bank rate is seeded unverified, interpretations are tiered, and the pack states it is not certified |
| Claims checked against the workspace | Mostly met. Two unverified statements were caught and removed from the handover (5.1). One wrong date reached `DESIGN.md` (F4) |

## 8. Recommended next steps
1. Fix the stale documentation (F4, F5, F6) and re-measure contrast for the new tokens (F3).
2. Phase 6: authentication, sessions and ownership checks on every case route (F1). The brief for this has been drafted but not started.
3. Commission advocate review of LR-01 to LR-25 (F2).
4. Add tests for the uncovered pack paths (F7) and investigate the mobile tab-bar flake (F10).

---

## 9. Follow-up (25 Oct 2026, Phase 6 session)

Sections 1–8 above are kept unchanged as the original audit record. This table records what happened to each finding afterwards.

| # | Status | What was done / what remains |
| --- | --- | --- |
| F1 | **Resolved (with limits)** | Phase 6 added signup, login, logout and me with Argon2id passwords and revocable server-side sessions, plus ownership checks on every supplier route (another supplier's records answer 404). Remaining: password change and reset, onboarding, a production deployment path. See DECISIONS.md Section 8 and HANDOVER.md |
| F2 | Open | LR-01 to LR-25 still await advocate review |
| F3 | **Resolved** | Contrast recomputed for the current tokens (DESIGN.md 2.1). Two real violations fixed: control borders (2.0:1) moved to a new `control` token (3.2 to 3.8:1), and brass small text (3.6:1) replaced with `ink-muted`. `ink-faint` remains limited to placeholders on white inputs (4.8:1) and a decorative icon |
| F4 | **Resolved** | DESIGN.md date corrected to 25 Oct 2026; status line, visual direction, typography (Geist), type scale and PDF note updated |
| F5 | **Resolved** | HANDOVER.md rewritten for the committed redesign and Phase 6 |
| F6 | **Resolved** | README structure, status table and run instructions updated |
| F7 | Open | `services/pack.py` still about 88% (uncovered lines moved to 88, 102, 105–107 after the signature change); not gated |
| F8 | Open | Rate limiter still in memory (now also covers login and signup) |
| F9 | Open | Same API-driven UI limits |
| F10 | Changed | The mobile tab-bar flake was not seen again. A different timing issue appeared: with 4 Playwright workers on a heavily loaded host (load average about 28 to 50, including a developer `make dev` session and the macOS malware scanner), 2 of 30 tests timed out while the Next.js dev server compiled routes. With 2 workers, 30 of 30 passed. See HANDOVER.md Section 7 |
