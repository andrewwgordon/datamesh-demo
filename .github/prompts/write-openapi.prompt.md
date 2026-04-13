---
version: 1
---
# Write OpenAPI (Data Plane / Control Plane)

## Purpose
Create or update OpenAPI specs under `contracts/openapi/` and align implementation.

## Inputs
- Which plane: data | control
- Endpoints to add/modify
- Auth requirements (OIDC bearer tokens)

## Guardrails
- Use OpenAPI **3.1.0**.
- Keep schemas reusable under `components/schemas`.
- Use consistent error model and status codes.
- Do not break existing endpoints without version bump.

## Steps
1) Update OpenAPI spec first.
2) Generate/confirm server URLs and base paths (`/api`, `/cp`).
3) Add request/response schemas.
4) Add security scheme (bearer JWT) and apply to operations.
5) Add contract validation tests.
6) Ensure service implementation matches (or create a ticket).

## Output
- Updated OpenAPI YAML
- Sample curl commands
- Tests and verification steps
