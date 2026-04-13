---
version: 1
---
# Add End-to-End Tests (Full PoC Scenario)

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
