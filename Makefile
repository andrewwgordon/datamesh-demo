up:
	docker compose -f platform/docker-compose.yml up -d

down:
	docker compose -f platform/docker-compose.yml down -v

bootstrap:
	bash platform/bootstrap/00_create_topics.sh
	bash platform/bootstrap/01_register_artifacts.sh
	bash platform/bootstrap/02_seed_keycloak.sh
	python platform/bootstrap/03_init_db.py

validate:
	python -m pytest -q tests/contract_validation

test: test-unit test-integration

test-unit:
	python -m pytest -q tests/phase_c/test_unit_db_kafka.py

test-integration:
	python -m pytest -q tests/phase_c/test_integration.py

e2e:
	python -m pytest -q -m e2e

demo: up bootstrap test
	@echo "Run demo script steps from docs/RUNBOOK.md"
