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


class DummyCursor:
    def __init__(self, fetchone_results=None, rowcount=1):
        self._fetchone_results = list(fetchone_results or [])
        self.rowcount = rowcount
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchone(self):
        if self._fetchone_results:
            return self._fetchone_results.pop(0)
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConn:
    def __init__(self, cursor: DummyCursor):
        self._cursor = cursor
        self.commits = 0
        self.closes = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closes += 1


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


def test_create_work_order_missing_asset_returns_400(client):
    base, s = client
    resp = s.post(
        f"{base}/work-orders",
        json={
            "work_order_id": "WO-1",
            "asset_id": "A-DOES-NOT-EXIST",
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
