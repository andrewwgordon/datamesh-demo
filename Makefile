up:
	docker compose -f platform/docker-compose.yml up -d

down:
	docker compose -f platform/docker-compose.yml down -v

bootstrap:
	bash platform/bootstrap/00_create_topics.sh
	bash platform/bootstrap/01_register_artifacts.sh
	bash platform/bootstrap/02_seed_keycloak.sh
	psql "$${POSTGRES_DSN:-postgresql://postgres:postgres@localhost:5432/eam}" -f platform/bootstrap/03_init_db.sql

validate:
	python -m pytest -q tests/contract_validation

test:
	python -m pytest -q

e2e:
	python -m pytest -q -m e2e

demo: up bootstrap test
	@echo "Run demo script steps from docs/RUNBOOK.md"
