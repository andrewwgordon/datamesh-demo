#!/usr/bin/env python3
"""
Database Bootstrap Script

This script initializes the PostgreSQL database schema for the EAM Maintenance PoC using the SQL statements from the existing 03_init_db.sql file.
It uses the psycopg2 library to connect to the database, wait until the database is ready, and then execute the SQL script.

Usage:
    python3 03_init_db.py

Environment Variables (defaults provided):
    POSTGRES_HOST         (default: localhost)
    POSTGRES_PORT         (default: 5432)
    POSTGRES_DB           (default: eam)
    POSTGRES_USER         (default: postgres)
    POSTGRES_PASSWORD     (default: postgres)
    POSTGRES_DSN          (optional, overrides individual parameters)

Configuration:
    Max Attempts: 30
    Retry Delay: 3 seconds
"""

import os
import sys
import time
import psycopg2
from pathlib import Path

# Database configuration from environment
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "eam")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Optionally, use DSN if provided
POSTGRES_DSN = os.getenv("POSTGRES_DSN")

# Wait configuration
MAX_ATTEMPTS = 30
RETRY_DELAY = 3  # seconds


def get_connection():
    """Returns a psycopg2 connection using DSN or individual parameters."""
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


def wait_for_postgres():
    """Waits until PostgreSQL is ready to accept connections."""
    endpoint = POSTGRES_DSN if POSTGRES_DSN else f"{DB_HOST}:{DB_PORT}"
    print(f"[db] Waiting for PostgreSQL at {endpoint}...")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"[db] Attempt {attempt}/{MAX_ATTEMPTS}...")
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            print("[db] ✓ PostgreSQL is ready!")
            return True
        except Exception as e:
            print(f"[db] Connection attempt failed: {e}")
            time.sleep(RETRY_DELAY)
    print(f"[db] ✗ ERROR: PostgreSQL not ready after {MAX_ATTEMPTS} attempts.")
    return False


def execute_sql_file(conn, sql_file_path):
    """Executes the SQL statements in the given file using the provided connection."""
    print(f"[db] Reading SQL file: {sql_file_path}")
    if not os.path.exists(sql_file_path):
        print(f"[db] ✗ ERROR: SQL file not found: {sql_file_path}")
        return False
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    print("[db] Executing SQL script...")
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
        conn.commit()
        print("[db] ✓ Database schema initialized successfully!")
        return True
    except Exception as e:
        print(f"[db] ✗ ERROR: Failed to execute SQL script: {e}")
        conn.rollback()
        return False


def main():
    print("[db] Starting database bootstrap...")
    # Determine the root directory assuming this file is in platform/bootstrap/
    root_dir = Path(__file__).parent.parent
    # The SQL file is expected to be at platform/bootstrap/03_init_db.sql
    sql_file = root_dir / "bootstrap" / "03_init_db.sql"
    if not sql_file.exists():
        print(f"[db] ✗ ERROR: SQL file not found: {sql_file}")
        sys.exit(1)
    if not wait_for_postgres():
        sys.exit(1)
    try:
        conn = get_connection()
        print(f"[db] Connected to database: {DB_NAME}")
        if execute_sql_file(conn, str(sql_file)):
            print("[db] ✓ Bootstrap completed successfully!")
            conn.close()
            sys.exit(0)
        else:
            print("[db] ✗ Bootstrap failed!")
            conn.close()
            sys.exit(1)
    except Exception as e:
        print(f"[db] ✗ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
