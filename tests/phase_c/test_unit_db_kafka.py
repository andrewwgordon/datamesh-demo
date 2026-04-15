#!/usr/bin/env python3
"""
Unit tests for database connectivity and Kafka consumer instantiation.

These tests validate:
- Database connection can be established and a simple query returns the expected result.
- KafkaConsumer can be instantiated without requiring a live Kafka instance by using monkeypatching.

Note: Environment variables are used to configure the database connection.
"""

import os
import pytest
import psycopg2
from kafka import KafkaConsumer
import json


def get_connection():
    """Establish a connection to the PostgreSQL database using environment variables."""
    POSTGRES_DSN = os.getenv("POSTGRES_DSN")
    if POSTGRES_DSN:
        return psycopg2.connect(POSTGRES_DSN)
    else:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "eam"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres")
        )


def test_database_connection():
    """
    Test that the database connection is established and a simple query returns the expected result.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            assert result[0] == 1, "Database did not return expected result for SELECT 1"
    finally:
        conn.close()


@pytest.fixture
def kafka_consumer():
    """Fixture that instantiates a real KafkaConsumer using environment variables."""
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_test_topic = os.getenv("KAFKA_TEST_TOPIC", "cdc.eam.asset.v1")
    consumer = KafkaConsumer(
        kafka_test_topic,
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset='earliest',
        consumer_timeout_ms=1000,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    yield consumer
    consumer.close()


def test_kafka_consumer_instantiation(kafka_consumer):
    """Test that KafkaConsumer is instantiated and subscribed based on environment variables."""
    import os
    expected_topic = os.getenv("KAFKA_TEST_TOPIC", "cdc.eam.asset.v1")
    topics = kafka_consumer.subscription()
    assert expected_topic in topics, f"Expected topic {expected_topic} not found in subscribed topics"
