# Copilot Instructions — EAM Maintenance PoC

## Follow AGENTS.md
AGENTS.md is the authoritative execution plan. Implement one ticket per PR.

## Rules
- Contracts-first: update JSON Schemas + AsyncAPI + OpenAPI before code changes.
- All runtime is Docker Compose.
- Every ticket must include tests.
- CDC is row-level with before+after.
- ECST snapshot includes embedded Asset summary.
- If ambiguous, ask a question rather than guessing.

## Commands
Use: make up, make bootstrap, make validate, make test, make e2e, make demo
