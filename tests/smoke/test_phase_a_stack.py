import json
import subprocess

import pytest


SERVICES = [
    "postgres",
    "kafka",
    "apicurio",
    "marquez-api",
    "marquez-web",
    "keycloak",
]


def _compose_ps_service_status():
    cmd = [
        "docker",
        "compose",
        "-f",
        "platform/docker-compose.yml",
        "-f",
        ".devcontainer/docker-compose.codespaces.yml",
        "ps",
        "--format",
        "json",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        pytest.skip(f"docker compose unavailable: {exc}")

    payload = result.stdout.strip()
    if not payload:
        pytest.skip("no docker compose services are running")

    if payload.startswith("["):
        rows = json.loads(payload)
    else:
        rows = [json.loads(line) for line in payload.splitlines() if line.strip()]

    if not rows:
        pytest.skip("no docker compose services found")
    return rows


def test_phase_a_core_services_present_in_compose_ps():
    rows = _compose_ps_service_status()
    for service in SERVICES:
        assert any(row.get("Service") == service for row in rows), f"missing service: {service}"


def test_phase_a_core_services_running_or_healthy():
    rows = _compose_ps_service_status()
    for service in SERVICES:
        matches = [row for row in rows if row.get("Service") == service]
        assert matches, f"service not found: {service}"
        row = matches[0]
        state_text = f"{row.get('State', '')} {row.get('Health', '')}".lower()
        assert ("running" in state_text) or ("healthy" in state_text), f"service not running: {service}"