---
version: 1
---
# Register Artifacts in Apicurio

## Purpose
Implement idempotent artifact registration of schemas/specs into Apicurio via bootstrap script.

## Inputs
- Apicurio base URL and credentials (if any)
- Artifact list:
  - artifactId
  - artifactType (OPENAPI, ASYNCAPI, JSON)
  - file path
  - groupId (optional)

## Guardrails
- Script must be **idempotent**: safe to run multiple times.
- Set at least content validity rule; set compatibility rule where appropriate.
- Fail fast with actionable errors.

## Steps
1) Implement `platform/bootstrap/01_register_artifacts.sh`.
2) For each artifact:
   - create if missing
   - update version if changed
3) Apply rules:
   - validity for all
   - backward compatibility for public schemas
4) Add a smoke check:
   - list artifacts and verify presence

## Output
- Updated bootstrap script
- Documentation in `docs/RUNBOOK.md` for artifact registration
- Commands to verify in Codespaces
