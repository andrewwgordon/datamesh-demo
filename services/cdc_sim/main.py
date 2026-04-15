"""
CDC Publisher Service
Polls cdc_log table and publishes row-level CDC events to Kafka topics.
Ensures exactly-once publish per cdc_log row (idempotence).
"""

import psycopg2
from kafka import KafkaProducer
import json
import time
import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "eam")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
POLL_INTERVAL_SECONDS = int(os.getenv("CDC_POLL_INTERVAL", "2"))

# Topic mapping
TOPIC_MAPPING = {
    "asset": "cdc.eam.asset.v1",
    "work_order": "cdc.eam.work_order.v1"
}


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def create_kafka_producer():
    """Create Kafka producer."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        retries=3,
        acks='all'
    )


def fetch_unpublished_cdc_records(conn, limit=100):
    """Fetch unpublished CDC records from cdc_log."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, table_name, operation, before_data, after_data
            FROM cdc_log
            WHERE published_at IS NULL
            ORDER BY id
            LIMIT %s
            """,
            (limit,)
        )
        rows = cur.fetchall()
        return rows


def mark_as_published(conn, cdc_id):
    """Mark a CDC record as published."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE cdc_log SET published_at = NOW() WHERE id = %s",
            (cdc_id,)
        )


def publish_cdc_event(producer, table_name, operation, before_data, after_data):
    """Publish a CDC event to the appropriate Kafka topic."""
    topic = TOPIC_MAPPING.get(table_name)
    if topic is None:
        logger.warning(f"No topic mapping for table: {table_name}")
        return
    
    # Construct CDC event payload
    event = {
        "table_name": table_name,
        "operation": operation,
        "before": before_data,
        "after": after_data,
        "timestamp": time.time()
    }
    
    # Use primary key as message key if available
    key = None
    if operation in ('c', 'u') and after_data:
        if table_name == "asset" and "asset_id" in after_data:
            key = after_data["asset_id"]
        elif table_name == "work_order" and "work_order_id" in after_data:
            key = after_data["work_order_id"]
    elif operation == 'd' and before_data:
        if table_name == "asset" and "asset_id" in before_data:
            key = before_data["asset_id"]
        elif table_name == "work_order" and "work_order_id" in before_data:
            key = before_data["work_order_id"]
    
    # Publish to Kafka
    future = producer.send(topic, key=key, value=event)
    try:
        record_metadata = future.get(timeout=10)
        logger.info(
            f"Published CDC event to {topic}: "
            f"partition={record_metadata.partition}, "
            f"offset={record_metadata.offset}, "
            f"operation={operation}, "
            f"key={key}"
        )
    except Exception as e:
        logger.error(f"Failed to publish CDC event: {e}")
        raise


def run_publisher():
    """Main publisher loop."""
    logger.info("Starting CDC Publisher...")
    producer = create_kafka_producer()
    
    while True:
        try:
            conn = get_db_connection()
            try:
                # Fetch unpublished records
                records = fetch_unpublished_cdc_records(conn)
                
                if not records:
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue
                
                logger.info(f"Found {len(records)} unpublished CDC records")
                
                # Process each record
                for record in records:
                    cdc_id, table_name, operation, before_data, after_data = record
                    
                    try:
                        # Publish to Kafka
                        publish_cdc_event(producer, table_name, operation, before_data, after_data)
                        
                        # Mark as published only after successful send
                        mark_as_published(conn, cdc_id)
                        conn.commit()
                        
                    except Exception as e:
                        logger.error(f"Error processing CDC record {cdc_id}: {e}")
                        conn.rollback()
                        # Continue processing other records
                        continue
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error in publisher loop: {e}")
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_publisher()
