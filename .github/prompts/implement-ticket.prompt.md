---
version: 1
---
# Implement Ticket (One PR)

## Purpose
Implement **exactly one** ticket from **AGENTS.md** end-to-end (code + tests + docs), suitable for a single PR.

## Inputs you must ask for (if not provided)
- Ticket ID (e.g., C2, D2) and the exact text from AGENTS.md
- Target language/framework constraints (default: Python/FastAPI)

## Guardrails
- Do **not** expand scope beyond the selected ticket.
- Follow **contracts-first**: if behavior affects payloads or APIs, update JSON Schema/AsyncAPI/OpenAPI **before** code.
- Add or update tests (unit + integration). If cross-service behavior changes, add/extend e2e.
- Keep changes small and reviewable; prefer multiple commits.

## Step-by-step workflow
1) **Restate** the ticket goal and acceptance criteria.
2) **List impacted artifacts**:
   - contracts (schemas/specs)
   - services and files
   - bootstrap scripts
3) **Plan**: 5–10 bullet steps you will execute.
4) **Implement** in small increments.
5) **Test**:
   - unit tests (fast)
   - integration tests (service/compose-level)
   - e2e updates if needed
6) **Update docs**:
   - README/RUNBOOK/AGENTS.md only if required
7) **Verification commands** (must run in Codespaces):
   - make validate
   - make test
   - make e2e (if relevant)

## Output format
- Summary of changes
- Files changed/added
- How to run/verify
- Any follow-up issues
