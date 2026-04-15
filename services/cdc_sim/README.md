# CDC Publisher Service

Polls the `cdc_log` table and publishes row-level CDC events to Kafka topics.

## Features

- Polls unpublished CDC records from `cdc_log`
- Publishes to appropriate Kafka topics based on table name
- Ensures exactly-once publish per `cdc_log` row (idempotence)
- Marks records as published only after successful Kafka send

## Configuration

Environment variables:
- `POSTGRES_HOST` - PostgreSQL host (default: postgres)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_DB` - Database name (default: eam)
- `POSTGRES_USER` - Database user (default: eam)
- `POSTGRES_PASSWORD` - Database password (default: eam)
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka bootstrap servers (default: kafka:29092)
- `CDC_POLL_INTERVAL` - Poll interval in seconds (default: 2)

## Running

```bash
pip install -r requirements.txt
python main.py
```

## Topics

- `cdc.eam.asset.v1` - CDC events for asset table
- `cdc.eam.work_order.v1` - CDC events for work_order table
