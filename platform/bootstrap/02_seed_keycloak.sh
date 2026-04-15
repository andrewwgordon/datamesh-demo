#!/usr/bin/env bash
set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8081}"
REALM="${KEYCLOAK_REALM:-datamesh}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
CLIENT_ID="${KEYCLOAK_CLIENT_ID:-data-product-api}"
CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-data-product-secret}"
DEMO_USER="${KEYCLOAK_DEMO_USER:-demo}"
DEMO_PASSWORD="${KEYCLOAK_DEMO_PASSWORD:-demo123}"

wait_for_keycloak() {
echo "[keycloak] Waiting for Keycloak at ${KEYCLOAK_URL}..."
local max_attempts=30
local attempt=1
while [ $attempt -le $max_attempts ]; do
echo "[keycloak] Attempt $attempt/$max_attempts..."
# Keycloak serves realms on the main HTTP port; use that as readiness signal
if curl -fsS --connect-timeout 5 "${KEYCLOAK_URL}/realms/master" >/dev/null 2>&1; then
echo "[keycloak] ✓ Keycloak is ready!"
return 0
fi
sleep 3
attempt=$((attempt + 1))
done
echo "[keycloak] ✗ ERROR: Keycloak not ready after $max_attempts attempts."
return 1
}

get_admin_token() {
# All log messages go to stderr so only the token is on stdout
echo "[keycloak] Obtaining admin token..." >&2
local response
response=$(curl -sS -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
-H "Content-Type: application/x-www-form-urlencoded" \
--data-urlencode "grant_type=password" \
--data-urlencode "client_id=admin-cli" \
--data-urlencode "username=${ADMIN_USER}" \
--data-urlencode "password=${ADMIN_PASSWORD}" 2>/dev/null)

if [[ $? -ne 0 || -z "$response" ]]; then
echo "[keycloak] ✗ ERROR: Failed to connect to Keycloak token endpoint" >&2
return 1
fi

local token
token=$(echo "$response" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')

if [[ -z "$token" ]]; then
echo "[keycloak] ✗ ERROR: Failed to extract access token" >&2
echo "[keycloak] Response: $response" >&2
return 1
fi

echo "$token"
}

ensure_realm() {
local token="$1"
echo "[keycloak] Checking realm: ${REALM}..."

if curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}" -H "Authorization: Bearer ${token}" >/dev/null 2>&1; then
echo "[keycloak] ✓ Realm already exists: ${REALM}"
return 0
fi

echo "[keycloak] Creating realm: ${REALM}..."
local http_code
http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${KEYCLOAK_URL}/admin/realms" \
-H "Authorization: Bearer ${token}" \
-H "Content-Type: application/json" \
-d "{\"realm\":\"${REALM}\",\"enabled\":true}")

if [[ "$http_code" -eq 201 ]]; then
echo "[keycloak] ✓ Realm created: ${REALM}"
else
echo "[keycloak] ✗ Failed to create realm (HTTP $http_code)"
return 1
fi
}

ensure_client() {
local token="$1"
echo "[keycloak] Checking client: ${CLIENT_ID}..."

local existing
existing=$(curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" -H "Authorization: Bearer ${token}")

if [[ "$existing" == "[]" ]]; then
echo "[keycloak] Creating client: ${CLIENT_ID}..."
local http_code
http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
-H "Authorization: Bearer ${token}" \
-H "Content-Type: application/json" \
-d "{\"clientId\":\"${CLIENT_ID}\",\"enabled\":true,\"publicClient\":false,\"secret\":\"${CLIENT_SECRET}\",\"directAccessGrantsEnabled\":true,\"serviceAccountsEnabled\":true,\"standardFlowEnabled\":true,\"redirectUris\":[\"*\"]}")

if [[ "$http_code" -eq 201 ]]; then
echo "[keycloak] ✓ Client created: ${CLIENT_ID}"
else
echo "[keycloak] ✗ Failed to create client (HTTP $http_code)"
return 1
fi
else
echo "[keycloak] ✓ Client already exists: ${CLIENT_ID}"
fi
}

ensure_user() {
local token="$1"
echo "[keycloak] Checking user: ${DEMO_USER}..."

local users
users=$(curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}/users?username=${DEMO_USER}" -H "Authorization: Bearer ${token}")

if [[ "$users" == "[]" ]]; then
echo "[keycloak] Creating user: ${DEMO_USER}..."
local http_code
http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users" \
-H "Authorization: Bearer ${token}" \
-H "Content-Type: application/json" \
-d "{\"username\":\"${DEMO_USER}\",\"enabled\":true,\"credentials\":[{\"type\":\"password\",\"value\":\"${DEMO_PASSWORD}\",\"temporary\":false}]}")

if [[ "$http_code" -eq 201 ]]; then
echo "[keycloak] ✓ User created: ${DEMO_USER}"
else
echo "[keycloak] ✗ Failed to create user (HTTP $http_code)"
return 1
fi
else
echo "[keycloak] ✓ User already exists: ${DEMO_USER}"
fi
}

# Main execution
wait_for_keycloak
TOKEN="$(get_admin_token)"
if [[ -z "${TOKEN}" ]]; then
echo "[keycloak] ✗ ERROR: failed to obtain admin token"
exit 1
fi

ensure_realm "${TOKEN}"
ensure_client "${TOKEN}"
ensure_user "${TOKEN}"

echo "[keycloak] ✓ Done."
