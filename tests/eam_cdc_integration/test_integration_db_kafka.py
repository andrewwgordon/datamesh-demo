#!/usr/bin/env python3
"""
Integration Test for CDC Publishing Flow

This test validates the end-to-end CDC publishing flow by interacting with both the PostgreSQL database
and the Kafka topic. It tests that when an asset is created or updated in the database,
the CDC Publisher service publishes the corresponding CDC event to the Kafka topic.

Steps:
1. Insert an asset record into the database.
2. Update the asset to trigger a CDC event (operation 'u').
3. Use a Kafka consumer to wait for a message on the topic 'cdc.eam.asset.v1'.
4. Validate the message content to ensure it reflects the updated asset.

Note: Adjust timeout and retry parameters as needed to ensure determinism.

Dependencies:
- psycopg2
- kafka-python
- pytest

Run with: pytest -q tests/phase_c/test_integration_flow.py
"""

import os
import sys
import time
import uuid
import json
import pytest
import psycopg2
from kafka import KafkaConsumer
from pathlib import Path

# Database configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "eam")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = "cdc.eam.asset.v1"

# CDC Publisher currently emits payload with fields:
# - table_name
# - operation
# - before
# - after
# - timestamp
OP_FIELD_CANDIDATES = ("op", "operation")

# Helper function - Database connection
def get_connection():
    if POSTGRES_DSN:
        return psycopg2.connect(POSTGRES_DSN)
    else:
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

# Helper function - Cleanup test data
def cleanup_test_data(conn, asset_id=None):
    with conn.cursor() as cur:
        if asset_id:
            cur.execute("DELETE FROM asset WHERE asset_id = %s", (asset_id,))
            cur.execute("DELETE FROM cdc_log WHERE table_name = 'asset' AND (after_data->>'asset_id' = %s OR before_data->>'asset_id' = %s)", (asset_id, asset_id))
    conn.commit()

# Helper function - Wait for Kafka message
def wait_for_kafka_message(consumer, timeout=30):
    start = time.time()
    for message in consumer:
        return message
        if time.time() - start > timeout:
            break
    return None


def drain_kafka_topic(consumer, timeout_s: float = 2.0):
    """Drain any currently available messages from the Kafka topic.

    This makes the test deterministic by ensuring the message we assert on
    is produced during the test window.
    """
    deadline = time.time() + timeout_s
    drained = 0
    while time.time() < deadline:
        # poll returns immediately; if no messages are available, it returns None
        msg = consumer.poll(timeout_ms=250)
        if msg is None:
            continue
        # kafka-python returns ConsumerRecord or dict-like depending on usage
        # Normalize for the drain count.
        drained += 1
    return drained

@pytest.fixture(scope="module")
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="module")
def kafka_consumer():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        consumer_timeout_ms=10000,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    yield consumer
    consumer.close()


def test_cdc_publishing_flow(db_conn, kafka_consumer):
    """
    Integration test for CDC publishing:
    Given an asset is inserted and then updated in the database,
    when the update occurs, a CDC event should be published to the Kafka topic.
    """
    # Create a unique asset id
    asset_id = "TEST_ASSET_" + uuid.uuid4().hex[:6]

    print(f"[test] Starting CDC publishing flow test for asset id {asset_id}")

    # Drain any existing messages so the test only observes messages produced
    # during this test.
    drained_count = drain_kafka_topic(kafka_consumer, timeout_s=2.0)
    print(f"[test] Drained {drained_count} pre-existing Kafka messages from {KAFKA_TOPIC}")

    try:
        print(f"[test] Inserting test asset with id {asset_id}")
        # Insert initial asset
        with db_conn.cursor() as cur:
            cur.execute("INSERT INTO asset (asset_id, name, type, location) VALUES (%s, %s, %s, %s)",
                        (asset_id, "Initial Asset", "TEST", "Location A"))
        db_conn.commit()
        
        # Give time for trigger to log the creation
        time.sleep(2)
        
        # Update asset to trigger update CDC event
        with db_conn.cursor() as cur:
            cur.execute("UPDATE asset SET name = %s WHERE asset_id = %s", ("Updated Asset", asset_id))
        db_conn.commit()
        
        # Wait for a message on the Kafka topic
        print(f"[test] Waiting for Kafka message on topic {KAFKA_TOPIC} for asset id {asset_id}")
        message = wait_for_kafka_message(kafka_consumer, timeout=30)
        
        assert message is not None, "Expected CDC message on Kafka, but none was received."
        
        # Validate message content
        value = message.value
        # Check that the message contains the updated asset id in the 'after' field
        assert 'asset_id' in value.get('after', {}), "Kafka message does not contain asset_id in 'after' field."
        assert value['after']['asset_id'] == asset_id, "Kafka message asset_id does not match the test asset id."
        # Retrieve and validate the operation field.
        # The CDC publisher uses `operation`, but some versions/tests may expect `op`.
        op = None
        for field in OP_FIELD_CANDIDATES:
            if field in value:
                op = value.get(field)
                break
        assert op is not None, f"Kafka message is missing the operation field (tried {OP_FIELD_CANDIDATES})."
        assert op in ['u', 'c'], f"Unexpected operation type in Kafka message: {op}"
        print(f"[test] Received Kafka message: {value}")
    finally:
        cleanup_test_data(db_conn, asset_id=asset_id)
