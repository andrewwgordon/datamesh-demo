# Normalizer Service

Transforms CDC events into canonical business events and maintains canonical state.

## Responsibilities

1. **Consumes CDC topics**:
   - `cdc.eam.asset.v1`
   - `cdc.eam.work_order.v1`

2. **Maintains asset state** for enrichment of work order events.

3. **Publishes business topics**:
   - `maintenance.workorder.notification.v1` (thin event with href)
   - `maintenance.workorder.snapshot.v1` (fat event with embedded asset summary)

4. **Updates canonical tables** in Postgres:
   - `canonical_asset`
   - `canonical_work_order`

5. **Emits OpenLineage events** to Marquez for data lineage tracking.

## Architecture

The normalizer:
- Maintains in-memory asset state for fast enrichment
- Falls back to database queries for missing asset data
- Ensures idempotent processing of duplicate events
- Emits lineage events showing data flow from CDC topics to business topics

## Configuration

Environment variables:
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: localhost:9092)
- `CDC_ASSET_TOPIC`: CDC asset topic (default: cdc.eam.asset.v1)
- `CDC_WORK_ORDER_TOPIC`: CDC work order topic (default: cdc.eam.work_order.v1)
- `NOTIFICATION_TOPIC`: Notification topic (default: maintenance.workorder.notification.v1)
- `SNAPSHOT_TOPIC`: Snapshot topic (default: maintenance.workorder.snapshot.v1)
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database connection
- `OPENLINEAGE_URL`: OpenLineage/Marquez URL (default: http://marquez:5000)
- `OPENLINEAGE_NAMESPACE`: OpenLineage namespace (default: eam-maintenance)
- `OPENLINEAGE_JOB_NAME`: OpenLineage job name (default: eam-cdc-to-canonical)

## Running

```bash
cd services/normalizer
pip install -r requirements.txt
python main.py
```

Or via Docker Compose (included in platform/docker-compose.yml).

## Event Flow

1. CDC events arrive from Kafka
2. Asset events update in-memory state and canonical_asset table
3. Work order events:
   - Enrich with asset summary from state or DB
   - Publish notification event (thin)
   - Publish snapshot event (fat with embedded asset)
   - Update canonical_work_order table
   - Emit OpenLineage events

## Idempotence

The service is designed to handle duplicate events:
- In-memory asset state is idempotent (same data overwrites)
- Database upserts handle duplicates
- Kafka producer handles retries