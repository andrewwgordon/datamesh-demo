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
	for _ in $(seq 1 90); do
		if curl -fsS "${KEYCLOAK_URL}/health/ready" >/dev/null 2>&1; then
			return 0
		fi
		sleep 2
	done
	echo "[keycloak] ERROR: Keycloak not ready."
	return 1
}

get_admin_token() {
	curl -fsS -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
		-H "Content-Type: application/x-www-form-urlencoded" \
		--data-urlencode "grant_type=password" \
		--data-urlencode "client_id=admin-cli" \
		--data-urlencode "username=${ADMIN_USER}" \
		--data-urlencode "password=${ADMIN_PASSWORD}" \
		| sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'
}

ensure_realm() {
	local token="$1"
	if curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}" -H "Authorization: Bearer ${token}" >/dev/null 2>&1; then
		echo "[keycloak] Realm exists: ${REALM}"
	else
		echo "[keycloak] Creating realm: ${REALM}"
		curl -fsS -X POST "${KEYCLOAK_URL}/admin/realms" \
			-H "Authorization: Bearer ${token}" \
			-H "Content-Type: application/json" \
			-d "{\"realm\":\"${REALM}\",\"enabled\":true}" >/dev/null
	fi
}

ensure_client() {
	local token="$1"
	local existing
	existing="$(curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" -H "Authorization: Bearer ${token}")"
	if [[ "${existing}" == "[]" ]]; then
		echo "[keycloak] Creating client: ${CLIENT_ID}"
		curl -fsS -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
			-H "Authorization: Bearer ${token}" \
			-H "Content-Type: application/json" \
			-d "{\"clientId\":\"${CLIENT_ID}\",\"enabled\":true,\"publicClient\":false,\"secret\":\"${CLIENT_SECRET}\",\"directAccessGrantsEnabled\":true,\"serviceAccountsEnabled\":true,\"standardFlowEnabled\":true,\"redirectUris\":[\"*\"]}" >/dev/null
	else
		echo "[keycloak] Client exists: ${CLIENT_ID}"
	fi
}

ensure_user() {
	local token="$1"
	local users
	users="$(curl -fsS "${KEYCLOAK_URL}/admin/realms/${REALM}/users?username=${DEMO_USER}" -H "Authorization: Bearer ${token}")"
	if [[ "${users}" == "[]" ]]; then
		echo "[keycloak] Creating user: ${DEMO_USER}"
		curl -fsS -X POST "${KEYCLOAK_URL}/admin/realms/${REALM}/users" \
			-H "Authorization: Bearer ${token}" \
			-H "Content-Type: application/json" \
			-d "{\"username\":\"${DEMO_USER}\",\"enabled\":true,\"credentials\":[{\"type\":\"password\",\"value\":\"${DEMO_PASSWORD}\",\"temporary\":false}]}" >/dev/null
	else
		echo "[keycloak] User exists: ${DEMO_USER}"
	fi
}

wait_for_keycloak
TOKEN="$(get_admin_token)"
if [[ -z "${TOKEN}" ]]; then
	echo "[keycloak] ERROR: failed to obtain admin token"
	exit 1
fi

ensure_realm "${TOKEN}"
ensure_client "${TOKEN}"
ensure_user "${TOKEN}"

echo "[keycloak] Done."
