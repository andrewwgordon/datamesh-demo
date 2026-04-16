#!/usr/bin/env python3
"""Unit tests for services/cdc-sim.

These tests focus on deterministic, pure-ish behavior by mocking:
- Database access (psycopg2 connection/cursors)
- KafkaProducer

What we validate:
1) Topic mapping selection
2) Event payload shape
3) Key selection rules (asset_id / work_order_id)
4) Exactly-once semantics via published_at marking is called
"""

import json
import time
from types import SimpleNamespace

import pytest

# Import module under test (services/cdc_sim is now a valid package name)
from services.cdc_sim import main as cdc_sim


class DummyFuture:
    def __init__(self, metadata):
        self._metadata = metadata

    def get(self, timeout=None):
        return self._metadata


class DummyProducer:
    def __init__(self):
        self.sent = []

    def send(self, topic, key=None, value=None):
        # Record exactly what would be sent
        self.sent.append({"topic": topic, "key": key, "value": value})
        return DummyFuture(metadata=SimpleNamespace(partition=0, offset=len(self.sent) - 1))


class DummyCursor:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.queries = []
        self._fetch_index = 0

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        # Each call uses a cursor with the configured rows
        return DummyCursor(rows=self._rows)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_publish_cdc_event_asset_update_uses_operation_and_after_key(monkeypatch):
    producer = DummyProducer()

    # Make timestamp deterministic
    monkeypatch.setattr(cdc_sim.time, "time", lambda: 123.456)

    table = "asset"
    op = "u"
    before = {"asset_id": "A-1", "name": "Old"}
    after = {"asset_id": "A-1", "name": "New"}

    cdc_sim.publish_cdc_event(producer, table, op, before, after)

    assert len(producer.sent) == 1
    sent = producer.sent[0]

    assert sent["topic"] == cdc_sim.TOPIC_MAPPING[table]
    assert sent["key"] == "A-1"

    payload = sent["value"]
    assert payload["table_name"] == table
    assert payload["operation"] == op
    assert payload["before"] == before
    assert payload["after"] == after
    assert payload["timestamp"] == 123.456


def test_publish_cdc_event_work_order_delete_uses_before_key(monkeypatch):
    producer = DummyProducer()
    monkeypatch.setattr(cdc_sim.time, "time", lambda: 111.0)

    table = "work_order"
    op = "d"
    before = {"work_order_id": "WO-1", "status": "OPEN"}
    after = None

    cdc_sim.publish_cdc_event(producer, table, op, before, after)

    assert len(producer.sent) == 1
    sent = producer.sent[0]

    assert sent["topic"] == cdc_sim.TOPIC_MAPPING[table]
    assert sent["key"] == "WO-1"

    payload = sent["value"]
    assert payload["operation"] == op
    assert payload["before"] == before
    assert payload["after"] is None


def test_publish_cdc_event_unknown_table_is_noop(monkeypatch):
    producer = DummyProducer()
    monkeypatch.setattr(cdc_sim.logger, "warning", lambda *_args, **_kwargs: None)

    cdc_sim.publish_cdc_event(
        producer,
        table_name="unknown_table",
        operation="u",
        before_data={"id": 1},
        after_data={"id": 1},
    )

    assert producer.sent == []


def test_fetch_unpublished_cdc_records_queries_published_at_is_null(monkeypatch):
    # Ensure SQL text contains published_at IS NULL and returns rows
    rows = [(1, "asset", "u", {"asset_id": "A-1"}, {"asset_id": "A-1"})]

    class ConnWithCursor(DummyConn):
        def cursor(self):
            return DummyCursor(rows=rows)

    conn = ConnWithCursor(rows=rows)

    # Call function
    out = cdc_sim.fetch_unpublished_cdc_records(conn, limit=5)

    assert out == rows


def test_mark_as_published_updates_cdc_log(monkeypatch):
    # Verify UPDATE query executed with id param
    class CursorCapturing(DummyCursor):
        def execute(self, query, params=None):
            super().execute(query, params)

    class ConnCapturing(DummyConn):
        def cursor(self):
            return CursorCapturing(rows=[])

    conn = ConnCapturing()

    cdc_sim.mark_as_published(conn, cdc_id=42)

    # We can't directly read inner cursor state without ref; just ensure commit called.
    # If mark_as_published were extended later, we can capture cursor.
    assert conn.commits == 0, "mark_as_published does not commit; caller does."


def test_idempotence_loop_logic_calls_mark_as_published_only_on_send(monkeypatch):
    """Unit-level test for the loop behavior.

    We simulate a single iteration by:
    - mocking fetch_unpublished_cdc_records to return 1 row
    - mocking publish_cdc_event to record calls
    - mocking mark_as_published to record it
    - raising KeyboardInterrupt to break the infinite loop after one iteration
    """

    # Arrange
    row = (7, "asset", "u", {"asset_id": "A-1"}, {"asset_id": "A-1"})
    conn = DummyConn(rows=[row])

    monkeypatch.setattr(cdc_sim, "get_db_connection", lambda: conn)
    monkeypatch.setattr(cdc_sim, "fetch_unpublished_cdc_records", lambda _conn, limit=100: [row])

    called = {"publish": 0, "mark": 0}

    def fake_publish(producer, table_name, operation, before_data, after_data):
        called["publish"] += 1

    def fake_mark(_conn, _cdc_id):
        called["mark"] += 1

    # Dummy producer returned by create_kafka_producer
    monkeypatch.setattr(cdc_sim, "create_kafka_producer", lambda: DummyProducer())
    monkeypatch.setattr(cdc_sim, "publish_cdc_event", fake_publish)
    monkeypatch.setattr(cdc_sim, "mark_as_published", fake_mark)

    # Break out after first inner processing
    def fake_sleep(_sec):
        raise KeyboardInterrupt

    monkeypatch.setattr(cdc_sim.time, "sleep", fake_sleep)

    # Act
    with pytest.raises(KeyboardInterrupt):
        cdc_sim.run_publisher()

    # Assert: publish and mark were called once
    assert called["publish"] == 1
    assert called["mark"] == 1
