# PaySetu: instructions for Claude Code

PaySetu is a LegalTech evidence-and-deadline tool for Indian micro and small suppliers under the MSMED Act. It prepares evidence; it does not give legal advice or file claims.

Before changing anything, read in this order:

1. `AGENTS.md`: mandatory coding and security rules.
2. `docs/HANDOVER.md`: current state, what is built, demo limits, next tasks.
3. `docs/DECISIONS.md`: decisions and open legal review items (LR-xx). Never implement against an Open item; use labelled defaults only.
4. `docs/IMPLEMENTATION_PLAN.md`: phases and task IDs.

Working rules for this project:

- Work on the current branch only. Do not commit, push, merge or switch branches unless the owner asks.
- Run `make lint`, `make typecheck` and `make test` before reporting a task done. Domain coverage must stay at 100%.
- Never weaken tests or add coverage exclusions to pass a check.
- Never invent a legal reading, a bank rate, a certification or a signature.
