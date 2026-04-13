---
version: 1
---
# Write JSON Schema (Contracts-First)

## Purpose
Create or modify JSON Schema(s) under `contracts/schemas/` for one message type.

## Inputs
- Schema name and version (e.g., `cdc.work_order.v1.schema.json`)
- Example payload(s) (at least one valid example; include edge cases)
- Backward-compatibility intent: none | backward | forward | full

## Guardrails
- Prefer **draft 2020-12** and include `$id`.
- Keep schemas **strict**: `additionalProperties: false` unless justified.
- Encode enums explicitly.
- If versioning changes are required, **create a new vN schema**, do not silently break.

## Steps
1) Determine the canonical `$id` naming convention (use `urn:schemas:<name>:v1`).
2) Define required fields and field types.
3) Add nullability explicitly (`type: ["string","null"]`).
4) Add `description` for non-obvious fields.
5) Provide:
   - at least 1 valid example
   - at least 2 invalid examples (explain why)
6) Add schema validation tests under `tests/contract_validation/`.

## Output
- Final JSON Schema(s)
- Example payloads (valid/invalid)
- Test updates and commands to run
