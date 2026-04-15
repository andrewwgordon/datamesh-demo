#!/usr/bin/env bash
set -euo pipefail

REGISTRY_URL="${REGISTRY_URL:-http://localhost:8080/apis/registry/v2}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

ARTIFACTS=(
	"JSON:contracts/schemas/cdc.asset.v1.schema.json:cdc.asset.v1.schema"
	"JSON:contracts/schemas/cdc.work_order.v1.schema.json:cdc.work_order.v1.schema"
	"JSON:contracts/schemas/canonical.asset.summary.v1.schema.json:canonical.asset.summary.v1.schema"
	"JSON:contracts/schemas/canonical.workorder.notification.v1.schema.json:canonical.workorder.notification.v1.schema"
	"JSON:contracts/schemas/canonical.workorder.snapshot.v1.schema.json:canonical.workorder.snapshot.v1.schema"
	# YAML files (AsyncAPI, OpenAPI, Contract) are stored in Apicurio as JSON
	# They can be registered separately after converting to JSON format
)

wait_for_registry() {
	echo "[registry] Waiting for Apicurio at ${REGISTRY_URL}..."
	for _ in $(seq 1 60); do
		if curl -fsS "${REGISTRY_URL}/system/info" >/dev/null 2>&1; then
			return 0
		fi
		sleep 2
	done
	echo "[registry] ERROR: Apicurio not reachable."
	return 1
}

mime_for_type() {
	case "$1" in
		AVRO|JSON) echo "application/json" ;;
		ASYNCAPI|OPENAPI|YAML) echo "application/yaml" ;;
		*) echo "application/octet-stream" ;;
	esac
}

register_or_update() {
	local type="$1"
	local rel_path="$2"
	local artifact_id="$3"
	local file_path="${ROOT_DIR}/${rel_path}"

	if [[ ! -f "${file_path}" ]]; then
		echo "[registry] Skip missing file: ${rel_path}"
		return 0
	fi

	local content_type
	content_type="$(mime_for_type "${type}")"

	# Ensure a basic global rule exists (validity) for artifact IDs used here.
	# Idempotent: update/create same rule endpoint each run.
	curl -fsS -X PUT \
		"${REGISTRY_URL}/admin/rules/VALIDITY" \
		-H "Content-Type: application/json" \
		-d '{"config":"FULL"}' >/dev/null 2>&1 || true

	if curl -fsS "${REGISTRY_URL}/groups/default/artifacts/${artifact_id}" >/dev/null 2>&1; then
		echo "[registry] Update artifact: ${artifact_id}"
		if ! curl -fsS -X PUT \
			"${REGISTRY_URL}/groups/default/artifacts/${artifact_id}" \
			-H "Content-Type: ${content_type}" \
			--data-binary "@${file_path}" 2>&1; then
			echo "[registry] WARNING: Failed to update artifact ${artifact_id}"
		fi
	else
		echo "[registry] Create artifact: ${artifact_id}"
		if ! curl -fsS -X POST \
			"${REGISTRY_URL}/groups/default/artifacts?artifactId=${artifact_id}&artifactType=${type}" \
			-H "Content-Type: ${content_type}" \
			--data-binary "@${file_path}" 2>&1; then
			echo "[registry] WARNING: Failed to create artifact ${artifact_id}"
		fi
	fi
}

wait_for_registry

for spec in "${ARTIFACTS[@]}"; do
	IFS=":" read -r type rel_path artifact_id <<<"${spec}"
	register_or_update "${type}" "${rel_path}" "${artifact_id}"
done

echo "[registry] Done."
