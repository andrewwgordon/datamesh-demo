#!/usr/bin/env bash
set -euo pipefail

KAFKA_CONTAINER="${KAFKA_CONTAINER:-datamesh-kafka}"
BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-kafka:9092}"

TOPICS=(
	"cdc.eam.asset.v1"
	"cdc.eam.work_order.v1"
	"maintenance.workorder.notification.v1"
	"maintenance.workorder.snapshot.v1"
)

echo "[topics] Waiting for Kafka container '${KAFKA_CONTAINER}' to be ready..."
for _ in $(seq 1 60); do
	if docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; then
		break
	fi
	sleep 2
done

if ! docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-topics.sh --bootstrap-server "${BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; then
	echo "[topics] ERROR: Kafka not ready after waiting."
	exit 1
fi

for topic in "${TOPICS[@]}"; do
	echo "[topics] Ensuring topic exists: ${topic}"
	docker exec "${KAFKA_CONTAINER}" /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server "${BOOTSTRAP_SERVER}" \
		--create \
		--if-not-exists \
		--topic "${topic}" \
		--replication-factor 1 \
		--partitions 1 >/dev/null
done

echo "[topics] Done."
