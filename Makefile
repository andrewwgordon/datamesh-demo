up:
	docker compose -f platform/docker-compose.yml up -d

bootstrap:
	bash platform/bootstrap/00_create_topics.sh
	bash platform/bootstrap/01_register_artifacts.sh
	bash platform/bootstrap/02_seed_keycloak.sh
	python platform/bootstrap/03_init_db.py

smoke-test:
	python -m pytest -q tests/smoke/

validate-contracts:
	python -m pytest -q tests/contract_validation

start-cdc:
	python services/cdc_sim/main.py &

start-eam:
	python services/eam_sim/main.py &

start-normalizer:
	python services/normalizer/main.py &

test: test-unit test-integration

test-unit:
	python -m pytest -q tests/cdc
	python -m pytest -q tests/eam
	python -m pytest -q tests/normalizer

test-integration:
	python -m pytest -q tests/eam_cdc_integration

stop-cdc:
	pkill -f "python services/cdc_sim/main.py"

stop-eam:
	pkill -f "python services/eam_sim/main.py"

stop-normalizer:
	pkill -f "python services/normalizer/main.py"

down:
	docker compose -f platform/docker-compose.yml down -v