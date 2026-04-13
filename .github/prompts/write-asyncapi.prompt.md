---
version: 1
---
# Write AsyncAPI (Kafka Topics)

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
