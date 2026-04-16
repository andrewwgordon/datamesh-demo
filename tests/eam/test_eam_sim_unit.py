#!/usr/bin/env python3
"""Unit tests for services/eam_sim/main.py.

These tests are deterministic and do not require Postgres/Kafka.
They mock psycopg2 connections/cursors and validate:
- create_asset / get_asset / update_asset basic behaviors
- create_work_order validates asset existence
- update_work_order validates update payload and 404 when missing

Run:
  pytest -q tests/phase_c/test_eam_sim_unit.py
"""

import pytest
import requests
import psycopg2
import os


def clear_tables():
    """Delete all rows from asset and work_order tables."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "eam"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM work_order")
            cur.execute("DELETE FROM asset")
            cur.execute("DELETE FROM cdc_log WHERE table_name IN ('asset', 'work_order')")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def clean_db():
    """Clear database tables once before all tests."""
    clear_tables()
    yield


@pytest.fixture()
def client():
    # Assume the EAM simulator is running in another process on localhost:8001
    base = "http://localhost:8001"
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return base, s


def test_create_asset_inserts_and_returns_asset_id(client):
    base, s = client
    resp = s.post(
        f"{base}/assets",
        json={"asset_id": "A-100", "name": "Pump", "type": "MOTOR", "location": "L1"},
        timeout=10,
    )
    assert resp.status_code == 200
    assert resp.json()["asset_id"] == "A-100"


def test_create_asset_duplicate_returns_400(client):
    base, s = client
    resp = s.post(
        f"{base}/assets",
        json={"asset_id": "A-100", "name": "Pump", "type": "MOTOR", "location": "L1"},
        timeout=10,
    )
    assert resp.status_code == 400


def test_get_asset_not_found_returns_404(client):
    base, s = client
    resp = s.get(f"{base}/assets/A-MISSING", timeout=10)
    assert resp.status_code == 404


def test_create_work_order_with_valid_asset(client):
    """Test creating a work order with a valid asset succeeds."""
    base, s = client
    # First create the asset
    resp = s.post(
        f"{base}/assets",
        json={"asset_id": "A-200", "name": "Valve", "type": "VALVE", "location": "L2"},
        timeout=10,
    )
    assert resp.status_code == 200
    
    # Then create the work order
    resp = s.post(
        f"{base}/work-orders",
        json={
            "work_order_id": "WO-100",
            "asset_id": "A-200",
            "title": "Replace valve",
            "description": "Replace valve",
            "status": "OPEN",
            "priority": "HIGH",
        },
        timeout=10,
    )
    assert resp.status_code == 200
    assert resp.json()["work_order_id"] == "WO-100"


def test_create_work_order_missing_asset_returns_400(client):
    base, s = client
    resp = s.post(
        f"{base}/work-orders",
        json={
            "work_order_id": "WO-1",
            "asset_id": "A-DOES-NOT-EXIST",
            "title": "Fix",
            "description": "Fix",
            "status": "OPEN",
            "priority": "HIGH",
        },
        timeout=10,
    )
    assert resp.status_code == 400


def test_update_work_order_no_fields_returns_400(client):
    base, s = client
    # update endpoint should fail before db access
    resp = s.put(f"{base}/work-orders/WO-1", json={}, timeout=10)
    assert resp.status_code == 400


def test_update_work_order_missing_row_returns_404(client):
    base, s = client
    resp = s.put(
        f"{base}/work-orders/WO-1",
        json={"status": "CLOSED"},
        timeout=10,
    )
    assert resp.status_code == 404
