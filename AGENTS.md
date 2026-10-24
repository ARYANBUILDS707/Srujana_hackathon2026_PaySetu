# PaySetu: Rules for Coding Agents

These rules apply to every AI coding agent and human contributor working on PaySetu. They are mandatory. If a rule blocks a task, stop and ask; do not work around it.

## 0. Sources of Truth

Read the relevant documents **before** changing anything:

| Document | Governs |
| --- | --- |
| `README.md` (root) | Project overview, current status, verified setup commands |
| `docs/PRD.md` | What to build, scope, legal rules (tiers S, I and C), decisions D1–D14 |
| `docs/DECISIONS.md` | Status of every architecture decision (ADR-xxx) and legal review item (LR-xx) |
| `docs/DESIGN.md` | Visual design, components, UX states, accessibility |
| `docs/ARCHITECTURE.md` | Stack, layers, folder structure, security boundaries |
| `docs/DATABASE.md` | Schema, constraints, triggers, ownership |
| `docs/API.md` | Endpoints, formats, errors, rate limits |
| `docs/IMPLEMENTATION_PLAN.md` | Phase order and task boundaries |

Precedence when documents conflict: **Accepted entries in DECISIONS.md > PRD > ARCHITECTURE > DATABASE > API > DESIGN > code**. Do not resolve a conflict silently. Report it and propose a document fix.

Before starting a task, check DECISIONS.md:

- Never implement against a decision whose status is `Open`. Ask instead.
- A `Proposed` decision may be built on only if the task says so, and the change must be easy to reverse.
- A legal item (LR-xx) that is not `Counsel-confirmed` must be implemented as a **labelled, configurable default**, never as settled law.

A requirement change goes into the documents first, in the same change set as the code.

---

## 1. Working Method

1. **Inspect before editing.** Read the files you will change and their callers and tests. Search for an existing helper before writing one.
2. **One task at a time.** Implement only the approved task. No drive-by refactors, renames or formatting of unrelated files.
3. **State your approach briefly** before large changes (more than about 5 files, or any schema/API change).
4. **Stop and ask** when:
   - the task is ambiguous
   - a legal rule seems wrong
   - a decision marked [DECISION] in PRD.md is still open
   - you need a new dependency
   - the change would alter the schema or the API contract beyond the task
5. **Never invent:** legal rules, statutory numbers, RBI rates, test results, provider behaviour or API fields. If information is missing, say so.
6. **Verify before reporting.** Run the relevant tests, linters and type checks. Report the actual output: what passed, what failed and what was not run.
7. **Keep the project runnable** after every task.

---

## 2. Project and Folder Structure

- Follow ARCHITECTURE.md Section 6 exactly. New top-level folders need a documentation update first.
- Backend layering is strict:
  - `api/` → `services/` → (`domain/`, `repositories/`, `storage/`, `documents/`, `integrations/`)
  - `domain/` is **pure**: no I/O, no database, no FastAPI/SQLAlchemy imports, no `datetime.now()`, no environment reads. "Today" is a parameter.
  - Routers never touch ORM models or sessions directly.
  - Repositories are the only place that builds queries.
- Frontend:
  - Pages live in `src/app/`.
  - Design-system primitives live in `src/components/ui/`; domain components live in `src/components/<domain>/`.
  - The API client lives in `src/lib/api/`, formatters in `src/lib/format/` and UI copy in `src/content/`.
- Tests mirror the source layout (`backend/tests/unit/domain/test_deemed_clock.py`).
- `README.md` and `AGENTS.md` live at the repository root. All other documentation lives in `docs/`.

---

## 3. Code Quality and Naming

### General

- Clear over clever. Small functions with one responsibility. Early returns over deep nesting.
- Comments explain **why**, especially for legal rules. Every legal computation cites its rule ID (e.g. `# R5: due before the appointed day`).
- No dead code, commented-out blocks or TODOs without a linked issue or plan task.
- Magic numbers are banned in legal logic. Periods, multipliers and caps come from the rule set (`rules/msmed-v1.toml`).

### Python

- Python 3.12, fully type-annotated. `mypy --strict` must pass on `app/domain/`; the rest of the code must pass mypy with the project config.
- Format and lint with Ruff. `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- Pydantic models: `XxxCreate`, `XxxUpdate`, `XxxOut`. Domain dataclasses: frozen.
- Money is `Decimal` (in the domain) or `int` paise (at the DB boundary). Never `float`.

### TypeScript

- `strict: true`; no `any` (use `unknown` and narrow); no non-null assertions without a comment explaining why.
- Use the generated OpenAPI types for every API shape. Never hand-write duplicates.
- `PascalCase` components, `camelCase` functions and variables, `kebab-case` file names except component files (`DayStrip.tsx`).
- ESLint + Prettier clean. No disabled lint rules without a justification comment.

### Naming consistency

Use the domain vocabulary from the PRD and DATABASE.md everywhere: `case`, `buyer_response`, `acceptance_state`, `due_date`, `interest_start`, `sealed_pack`, `share_link`, `evidence_item`, `timeline_event`. Do not introduce synonyms (no "claim", "order" or "dispute" for `case`; no "attachment" or "document" for `evidence_item`).

---

## 4. Component Reuse (Frontend)

- Use DESIGN.md components. Before creating a component, search `src/components/` for one that fits. Extending one with a prop beats duplicating it.
- Styling uses Tailwind classes mapped to DESIGN.md tokens only. No raw hex values, arbitrary pixel values outside the spacing scale, or inline styles (except computed widths in `DayStrip`).
- All money, date and hash display goes through `src/lib/format/`. No inline `toLocaleString` calls.
- All user-facing copy goes in `src/content/`. Buyer-facing and legal copy follows the voice rules in DESIGN.md Section 13.
- Every data-loading view implements the loading, empty and error states in PRD Section 13 / DESIGN.md Section 8.
- Accessibility (DESIGN.md Section 11) is part of "done": labels, focus, keyboard and contrast.

---

## 5. Dependency Management

- **No new dependency without approval.** The approved list is ARCHITECTURE.md Section 2. To add one, explain the need, the alternatives considered (including the standard library), its maintenance status and its licence, then wait for approval.
- Pin exact versions (`requirements*.txt`, `package-lock.json`). Commit the lockfiles.
- Never install packages globally or modify lockfiles for unrelated reasons.
- No packages that phone home (analytics, telemetry) and no CDN-loaded scripts.

---

## 6. Type Safety and Validation

- Validate every external input at the boundary: Pydantic on the API (`extra="forbid"`), magic-byte checks on files, and the config through `pydantic-settings`.
- The frontend validates for UX only. The server is authoritative.
- Do not weaken types or validation to make something compile or pass.
- Regenerate frontend API types after any API schema change, and commit them.

---

## 7. Error Handling

- Raise typed domain/service errors (`NotFound`, `Conflict`, `ValidationFailed`, `IntegrityFailed`, `IntegrationFailed`, `RateLimited`). The central handler maps them to `application/problem+json` (API.md Section 1.4).
- Never swallow exceptions. Never return 200 with an error body.
- Never expose stack traces, SQL, file paths or provider responses to clients.
- Show user-safe messages in the UI. Keep form input on errors.
- External calls always have timeouts. Retries only where API.md allows them (never for email sends).

---

## 8. Security and Secrets

1. **Never commit secrets.** Use environment variables only. `.env` is gitignored; `.env.example` contains names and placeholders only.
2. Never print, log or return secrets, passwords, session/share/reset tokens, cookies, file contents or email bodies. Redact tokens in logged paths.
3. **Authorisation is server-side, always.** Every supplier query is scoped by `supplier_id` in the repository. Cross-tenant access returns 404. Frontend route guards are UX only.
4. Every new endpoint needs: auth dependency, input schema, ownership check, rate-limit category and tests for 401/404-cross-tenant.
5. Unsafe methods enforce the CSRF rules (Origin + `X-PaySetu-Client` header).
6. Uploads: allowlist + magic bytes + size limits; never trust the client filename or MIME type; never execute, unzip or render uploaded content inline.
7. No `dangerouslySetInnerHTML`, no `eval`, no string-built SQL, no shell commands built from user input.
8. Share tokens and session tokens are stored hashed. Raw values are shown once.
9. Do not disable security headers, CSP, triggers or rate limits, even temporarily, to make a feature or test work.

---

## 9. Evidence, Legal Logic and Honesty (Product-Critical)

1. **Evidence bytes are sacred.** Never modify, re-encode, compress, resize or strip metadata from stored evidence. Hash the original bytes on the server.
2. **Append-only is non-negotiable.** Never add code paths that update or delete `evidence_items`, `timeline_events`, `sealed_packs` or `share_access_logs` beyond what DATABASE.md Section 6 allows. Never disable the triggers in application code.
3. Every state-changing case action writes a timeline event **in the same transaction**.
4. **No outbound communication without an approval event.** Code that sends anything to a buyer must check `status` and `approved_at`, and must be covered by a test.
5. **Legal state is computed, never stored.** Do not add columns for acceptance date, due date, interest or checklist status.
6. Legal rule changes require: a new rule-set version, updated fixtures in `tests/fixtures/legal/`, a PRD update and owner approval. Never "fix" a legal outcome by changing a test expectation without that process.
7. **Honest labels:** simulated or sandbox results must carry `mode`/`simulated` through the API, UI, PDFs and the manifest. Never present a simulated integration as live.
8. Never write copy that promises recovery, predicts outcomes or claims that hashing alone makes evidence admissible.
9. No AI/LLM features unless the PRD is updated and approved.

---

## 10. Database and API Access

- Schema changes go only through Alembic migrations that match DATABASE.md. Update DATABASE.md in the same change. Migrations are reviewed and never edited after merge.
- Use SQLAlchemy 2.0 typed models and parameterised queries only.
- One transaction per service method. No commits inside repositories or routers.
- Do not add indexes, tables or columns "for later".
- API changes must match API.md. Update API.md in the same change. Keep the conventions: snake_case, money as strings, problem+json errors, cursor pagination.
- The frontend accesses data only through `src/lib/api/`. Never call the database or secrets from Next.js.

---

## 11. Testing

| Change type | Required tests |
| --- | --- |
| `domain/` logic | Unit tests for every branch and boundary (Day 15 vs 16, month ends, leap years, the 45-day cap, rate changes, part payments). 100% branch coverage on `domain/` |
| Legal rules | Fixture-driven tests in `tests/fixtures/legal/`, including the interest reference fixture (Rs 5,00,000 at 17.25% for 12 months = Rs 93,406.72 exactly; a mathematical regression test, not proof of statutory correctness) |
| Endpoint | Integration tests: happy path, validation error, unauthenticated (401), cross-supplier (404), invalid state (409), rate limit where applicable |
| Evidence/timeline | Tamper tests: modified file bytes and an edited event row are detected; trigger tests prove UPDATE/DELETE are blocked |
| Communications | Tests that sending without approval is impossible and that double send is prevented |
| UI flow | Playwright for critical journeys (Ravi journey, share pages, revoked link) at 360×800 and 1280×800 |

Rules:

- Tests use a fresh temp database built with `alembic upgrade head` and a temp storage directory, plus the frozen injectable clock.
- Never delete, skip or weaken a failing test to get a green run. Investigate the failure.
- Never call real external services in tests. Use the simulated adapters or HTTP mocks.
- Never use real personal or business data in fixtures.

Before reporting a task done, run the relevant commands from the `Makefile`: `make lint`, `make typecheck`, `make test` (and `make e2e` for UI flows). `make test` fails if line or branch coverage of `backend/app/domain/` drops below 100%. Fix this by adding tests, never by adding coverage exclusions.

---

## 12. Documentation

- Update the relevant `docs/*.md` in the same change whenever behaviour, schema, API, configuration or dependencies change.
- Keep the root `README.md` "Current Implementation Status" and "Installation" sections accurate. Only document commands you have actually run successfully.
- When a decision or legal item changes status, update `docs/DECISIONS.md` in the same change.
- Public functions in `domain/` and `services/` have docstrings stating the inputs, outputs and the rule IDs applied.
- New environment variables are added to `.env.example` and ARCHITECTURE.md Section 12.

---

## 13. Git and Change Discipline

- Work on a feature branch named `phase-<n>/<short-task>` (e.g. `phase-2/deemed-clock-domain`). Never commit directly to `main`.
- Small, focused commits using the Conventional Commits style: `feat(clock): compute deemed acceptance (R1–R3)`, `fix(evidence): …`, `docs(api): …`, `test(interest): …`, `chore(deps): …`.
- One logical change per commit. No mixed refactor and feature commits.
- Do not commit generated build output, `storage/`, `.env`, databases or IDE files.
- Do not rewrite shared history (no force-push to shared branches).
- Commit or push only when the owner asks. Every PR description lists: the task, the files changed, the tests run with results, document updates and open questions.

---

## 14. Definition of Done (every task)

- [ ] Implements only the approved task; matches PRD, DESIGN, ARCHITECTURE, DATABASE and API
- [ ] Loading, empty, error and success states handled (UI tasks)
- [ ] Inputs validated and authorisation enforced server-side
- [ ] Timeline events written for case actions; append-only rules respected
- [ ] Tests added or updated; lint, typecheck and tests run and passing (output reported)
- [ ] No secrets, no new unapproved dependencies, no unrelated changes
- [ ] Documentation updated where behaviour changed
- [ ] Simulated or sandbox behaviour clearly labelled
