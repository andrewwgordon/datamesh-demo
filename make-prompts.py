from pathlib import Path

base = Path('.github/prompts')
base.mkdir(parents=True, exist_ok=True)

def write(name, text):
    (base / name).write_text(text, encoding='utf-8')

common_header = """---
version: 1
---
"""

write('implement-ticket.prompt.md', common_header + """# Implement Ticket (One PR)

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
""")

write('write-json-schema.prompt.md', common_header + """# Write JSON Schema (Contracts-First)

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
""")

write('write-asyncapi.prompt.md', common_header + """# Write AsyncAPI (Kafka Topics)

## Purpose
Create or update AsyncAPI specs under `contracts/asyncapi/` for Kafka topics.

## Inputs
- Topic names
- Whether this doc is for CDC or business topics
- Message schema `$ref` targets (JSON schema `$id` or local file refs)

## Guardrails
- Use AsyncAPI **3.0.0** unless tooling constraints force 2.x.
- Include Kafka **bindings** (topic name, partitions, replicas).
- Ensure channel addresses match deployed topics.
- Keep operationIds stable.

## Steps
1) Define `servers` for Kafka and document host/port placeholders.
2) Define `channels` with `address` and message references.
3) Add Kafka bindings under each channel.
4) Define `operations` for send/receive roles.
5) Reference payload schemas.
6) Add validation step (lint or parse) to `make validate`.

## Output
- Updated AsyncAPI YAML
- Notes on how to validate
- Any required bootstrap topic changes
""")

write('write-openapi.prompt.md', common_header + """# Write OpenAPI (Data Plane / Control Plane)

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
""")

write('register-apicurio.prompt.md', common_header + """# Register Artifacts in Apicurio

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
""")

write('emit-openlineage.prompt.md', common_header + """# Emit OpenLineage to Marquez

## Purpose
Add OpenLineage emission for the Normalizer job so lineage appears in Marquez.

## Inputs
- Job name (default: `eam-cdc-to-canonical`)
- Input datasets (CDC topics)
- Output datasets (business topics)
- Marquez/OpenLineage endpoint URL

## Guardrails
- Emit START and COMPLETE events.
- Include dataset identifiers consistently (`kafka://<topic>`).
- Do not emit extremely high-frequency events; batch by interval or count.

## Steps
1) Add `services/normalizer/app/lineage.py` with emitter functions.
2) Integrate emission into normalizer lifecycle:
   - START at run begin / interval
   - COMPLETE after processing window
3) Add configuration via env vars.
4) Add unit tests that validate payload structure.
5) Add integration note: how to confirm in Marquez UI.

## Output
- Lineage emitter implementation
- Tests
- Verification steps
""")

write('add-integration-tests.prompt.md', common_header + """# Add Integration Tests (Compose-backed)

## Purpose
Create integration tests that validate interactions across at least two components (DB/Kafka/services).

## Inputs
- Which flow to test (CDC publishing, normalization, API serving, consumer behavior)
- Expected artifacts (topics, DB rows, HTTP responses)

## Guardrails
- Tests must be deterministic.
- Prefer testcontainers if available, otherwise use compose services with waits/timeouts.
- Use small timeouts with retries.

## Steps
1) Identify test boundary and fixtures.
2) Implement helpers:
   - wait for Kafka topic message
   - query Postgres tables
   - call HTTP endpoints
3) Write tests with clear Given/When/Then comments.
4) Ensure tests are runnable via `make test`.

## Output
- Test code
- Helper utilities
- How to run
""")

write('add-e2e-tests.prompt.md', common_header + """# Add End-to-End Tests (Full PoC Scenario)

## Purpose
Add or extend e2e tests that run the full scenario:
EAM write → CDC → Normalizer → Business topics → Data Plane API → Consumers → Lineage

## Inputs
- Scenario steps (asset/work order IDs, status transitions)
- Assertions (messages, API outputs, consumer state, lineage presence)

## Guardrails
- Keep e2e runtime reasonable (<10 minutes).
- Use idempotent setup/teardown.
- Avoid flaky timing: use polling with deadlines.

## Steps
1) Bring up compose (or assume running) and verify health.
2) Execute EAM API operations.
3) Poll Kafka for CDC and business events.
4) Call Data Plane API and compare to expected canonical state.
5) Verify consumers processed events.
6) Verify lineage exists in Marquez (API query).

## Output
- e2e tests
- Any required Makefile updates (`make e2e`)
""")

# Provide a summary file listing prompts
summary = """# Prompt Templates

These prompt templates are designed for GitHub Copilot prompt files under `.github/prompts/`.
Use them to keep work consistent with **AGENTS.md**.

## Files
- implement-ticket.prompt.md
- write-json-schema.prompt.md
- write-asyncapi.prompt.md
- write-openapi.prompt.md
- register-apicurio.prompt.md
- emit-openlineage.prompt.md
- add-integration-tests.prompt.md
- add-e2e-tests.prompt.md
"""
Path('.github/prompts/README.md').write_text(summary, encoding='utf-8')

# return created files
sorted([str(p) for p in base.glob('*.prompt.md')]) + [str(Path('.github/prompts/README.md'))]
