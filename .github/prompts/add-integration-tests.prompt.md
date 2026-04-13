---
version: 1
---
# Add Integration Tests (Compose-backed)

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
