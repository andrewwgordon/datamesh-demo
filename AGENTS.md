AGENTS.md — EAM Maintenance History PoC (Codespaces + Copilot, all Docker Compose)
0) Purpose
This file is the authoritative runbook for an AI coding agent (and humans) to design, implement, test, and demo the PoC end-to-end.
Golden rule: Implement one ticket per PR. Do not expand scope.
---
1) PoC Goal (What we are proving)
Build a minimal Equipment Asset Management (EAM) simulator with only two entities (Asset, Work Order) backed by a relational database, and:
Emit row-level CDC events with before + after images to Kafka topics.
Transform CDC via an intermediate Normalizer into a canonical business object in a normalized, standards-oriented schema.
Provide two event-driven access styles from the canonical model:
Notification + Pull (thin event contains IDs + `href` to fetch full state via Data Plane OpenAPI)
ECST Snapshot (fat event contains WorkOrder snapshot with embedded Asset summary)
Expose Dual OpenAPI endpoints for the Data Product:
Data Plane: query canonical state
Control Plane: contract/spec discovery, subscription details, lineage links
Publish contracts to an artifact registry (Apicurio):
JSON Schemas
AsyncAPI specs
OpenAPI specs
Emit OpenLineage events from the Normalizer and visualize lineage in Marquez.
Secure OpenAPI endpoints with Keycloak (OIDC).
---
2) Non-Goals (Explicitly out of scope)
No additional EAM entities beyond Asset and WorkOrder.
No full data catalog UI beyond Apicurio + Marquez.
No production HA, multi-cluster, or Kubernetes deployment.
No complex RBAC/ABAC beyond minimal auth (Keycloak) and optional policy checks.
---
3) Architecture (Logical)
3.1 Dataflow
EAM Simulator writes Asset/WorkOrder rows to Postgres.
Postgres triggers write row change records (OLD/NEW) into `cdc_log`.
CDC Publisher reads `cdc_log` and publishes row-level CDC events to Kafka:
`cdc.eam.asset.v1`
`cdc.eam.work_order.v1`
Normalizer consumes CDC topics, maintains current state, and publishes business topics:
Notification+Pull: `maintenance.workorder.notification.v1`
ECST Snapshot: `maintenance.workorder.snapshot.v1`
It also writes canonical current state to `canonical_*` tables.
Data Product API serves canonical state from `canonical_*` tables:
Data Plane `/api/...`
Control Plane `/cp/...`
Consumers:
Notification+Pull consumer subscribes to `maintenance.workorder.notification.v1` and calls Data Plane `href`.
ECST consumer subscribes to `maintenance.workorder.snapshot.v1` and builds a local read model.
Lineage:
Normalizer emits OpenLineage START/COMPLETE with inputs (CDC topics) and outputs (business topics).
Marquez stores and displays lineage.
3.2 Interfaces (Contracts)
OpenAPI: Data Plane + Control Plane HTTP endpoints
AsyncAPI: Kafka topics for CDC + business events
JSON Schema: payload schemas referenced by AsyncAPI and used for runtime validation
---
4) Repository Layout (Monorepo)
```
.
├── AGENTS.md
├── README.md
├── Makefile
├── .github/
│   ├── copilot-instructions.md
│   ├── prompts/
│   └── workflows/
├── contracts/
│   ├── schemas/
│   ├── asyncapi/
│   ├── openapi/
│   └── contract/
├── platform/
│   ├── docker-compose.yml
│   └── bootstrap/
└── services/
    ├── eam-sim/
    ├── cdc-sim/
    ├── normalizer/
    ├── data-product/
    └── consumers/
        ├── notif-pull/
        └── ecst/
```
---
5) Contracts Inventory
5.1 Kafka Topics
CDC topics
`cdc.eam.asset.v1`
`cdc.eam.work_order.v1`
Business topics
`maintenance.workorder.notification.v1`
`maintenance.workorder.snapshot.v1`
5.2 Schemas (JSON Schema)
Store in `contracts/schemas/`:
`cdc.asset.v1.schema.json`
`cdc.work_order.v1.schema.json`
`canonical.asset.summary.v1.schema.json`
`canonical.workorder.notification.v1.schema.json`
`canonical.workorder.snapshot.v1.schema.json`
5.3 AsyncAPI
Store in `contracts/asyncapi/`:
`asyncapi-cdc.yaml`
`asyncapi-business.yaml`
5.4 OpenAPI
Store in `contracts/openapi/`:
`openapi-data.yaml`
`openapi-control.yaml`
5.5 Product Contract (ODCS-like)
Store in `contracts/contract/product.contract.yaml`:
Product metadata
Owners
SLA/SLO placeholders
Links/refs to OpenAPI + AsyncAPI artifacts
---
6) Services (Responsibilities)
6.1 platform (Compose + bootstrap)
`platform/docker-compose.yml`: Kafka, Postgres, Apicurio, Marquez, Keycloak, and all app services.
`platform/bootstrap/00_create_topics.sh`: create topics (idempotent).
`platform/bootstrap/01_register_artifacts.sh`: upload schemas/specs to Apicurio (idempotent).
`platform/bootstrap/02_seed_keycloak.sh`: seed realm/client/users (idempotent).
`platform/bootstrap/03_init_db.sql`: DB schema, triggers, canonical tables.
6.2 EAM Simulator (`services/eam-sim`)
Minimal REST API to create/update Assets and WorkOrders.
Writes to Postgres.
6.3 CDC Publisher (`services/cdc-sim`)
Polls `cdc_log` table.
Publishes CDC events (before/after) to Kafka.
Marks `cdc_log` records as published.
6.4 Normalizer (`services/normalizer`)
Consumes CDC topics.
Maintains in-memory (and/or DB) state stores.
Produces:
Notification+Pull events
ECST WorkOrder snapshot events with embedded Asset summary
Upserts canonical state into Postgres (`canonical_asset`, `canonical_work_order`).
Emits OpenLineage events to Marquez.
6.5 Data Product API (`services/data-product`)
Data Plane:
`GET /api/v1/assets/{assetId}`
`GET /api/v1/work-orders/{workOrderId}`
Control Plane:
`GET /cp/v1`
`GET /cp/v1/contract`
`GET /cp/v1/interfaces`
`POST /cp/v1/subscriptions`
`GET /cp/v1/lineage`
Secured with Keycloak OIDC.
6.6 Consumers (`services/consumers`)
`notif-pull`: consume notification events; fetch canonical WorkOrder via Data Plane `href`.
`ecst`: consume snapshot events; upsert into local store (SQLite) and provide a small CLI/query.
---
7) Development Workflow (All Docker Compose)
7.1 Commands (Make targets)
`make up` — start compose stack
`make down` — stop stack and remove volumes
`make bootstrap` — create topics, register Apicurio artifacts, seed Keycloak, init DB
`make validate` — validate schemas/specs
`make test` — unit + integration tests
`make e2e` — end-to-end tests
`make demo` — run demo script (writes + verifies outputs)
7.2 Required determinism rules
Contracts first: update schema/spec before code behavior changes.
No hidden state: everything is bootstrapped and reproducible.
Transform functions must be pure and unit-tested using golden JSON fixtures.
Idempotence:
topic creation, artifact registration, keycloak seeding
CDC publisher must not republish the same `cdc_log` row
Normalizer must tolerate duplicate events
---
8) Backlog (Epics → Tickets)
EPIC A — Platform (Compose)
A1 Compose stack for Kafka/Postgres/Apicurio/Marquez/Keycloak and app services.
Deliverables: `platform/docker-compose.yml`
Tests: smoke healthchecks
A2 Bootstrap scripts
`00_create_topics.sh`
`01_register_artifacts.sh`
`02_seed_keycloak.sh`
`03_init_db.sql`
Acceptance: `make up bootstrap` completes without manual steps.
EPIC B — Contracts-first
B1 JSON schemas (CDC + canonical)
Deliverables: `contracts/schemas/*.json`
Tests: schema validation on examples
B2 AsyncAPI (CDC + business topics)
Deliverables: `contracts/asyncapi/*.yaml`
B3 OpenAPI (Data Plane + Control Plane)
Deliverables: `contracts/openapi/*.yaml`
B4 Apicurio registration
Deliverables: bootstrap script, compatibility rules (at least validity)
Acceptance: Apicurio shows all artifacts and versions.
EPIC C — EAM + CDC
C1 EAM Simulator API
Endpoints to create/update Asset and WorkOrder.
C2 DB schema + triggers
Tables: `asset`, `work_order`, `cdc_log`, `canonical_asset`, `canonical_work_order`
Triggers write `OLD` and `NEW` into `cdc_log` as JSON.
C3 CDC Publisher
Poll `cdc_log`, publish to Kafka topics.
Exactly-once publish per `cdc_log` row (idempotence).
Acceptance: Update WO status produces CDC `u` event with before+after.
EPIC D — Normalizer (CDC → canonical)
D1 CDC consumers and state stores
Maintain asset state for enrichment.
D2 Canonical transform + emit
Publish notification + snapshot events for work_order changes.
Snapshot includes embedded asset summary.
D3 Canonical serving tables
Upsert canonical asset/work_order into Postgres.
D4 OpenLineage emission
Emit lineage with CDC topics as inputs and business topics as outputs.
Acceptance: Business topics populated; canonical tables updated; lineage visible in Marquez.
EPIC E — Data Product API (Dual OpenAPI)
E1 Data Plane API serving canonical state.
E2 Control Plane API returning:
contract YAML
interface pointers (Apicurio artifact refs)
subscription response (topic list + schema refs)
lineage pointers (Marquez URL/job)
E3 Keycloak auth middleware
Require bearer tokens for `/api` and `/cp`.
Acceptance: Consumers can use control plane to discover topics and data plane to fetch state.
EPIC F — Consumers
F1 Notification+Pull consumer
F2 ECST consumer (local read model)
Acceptance: both consumers demonstrate the two access patterns.
EPIC G — Testing + Demo
G1 Unit tests for transforms
G2 Integration tests across services
G3 E2E demo script
Create asset + WO
Update WO status OPEN→IN_PROGRESS→CLOSED
Verify CDC, business topics, data plane, consumers, lineage
Acceptance: `make demo` produces deterministic output and passes.
---
9) Testing Strategy
9.1 Unit tests
Transform functions (CDC → canonical)
Changed field detection from before/after
Asset enrichment logic
9.2 Integration tests
DB triggers generate `cdc_log` rows
CDC publisher emits Kafka messages
Normalizer produces business events + canonical table updates
Data Product API returns expected canonical state
9.3 End-to-End tests
Full compose up
Execute demo scenario
Assert:
CDC topics have messages
business topics have messages
notification consumer fetches via href
ECST consumer state updated
lineage events accepted by Marquez
---
10) Demo Script (Operator steps)
`make up`
`make bootstrap`
Use EAM API:
Create Asset A-10001
Create WorkOrder WO-90001 for A-10001 (status OPEN)
Update WO-90001 status to IN_PROGRESS
Update WO-90001 status to CLOSED
Verify:
CDC events on `cdc.eam.*`
Notification events on `maintenance.workorder.notification.v1`
Snapshot events on `maintenance.workorder.snapshot.v1` with embedded asset summary
Data Plane `GET /api/v1/work-orders/WO-90001` returns canonical state
Notification consumer performs pull via `href`
ECST consumer local store contains WO-90001
Marquez shows lineage graph for `eam-cdc-to-canonical`
---
11) Notes / Clarifications (decisions)
Delete semantics for WorkOrders: publish snapshot with `deleted=true` (recommended) OR notification-only. Decide before implementation.
Asset updates: keep minimal (no standalone asset business topic) unless needed.
---
12) Contribution Rules
One ticket per PR.
Update contracts before code.
Include tests.
Keep Compose reproducible.
