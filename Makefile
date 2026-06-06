# Atajos de desarrollo para Sofia AI DataOps.
# Objetivo: ejecutar tareas frecuentes sin recordar comandos largos.

.PHONY: setup lint test run docker-up docker-down airflow-lab-up airflow-lab-down reindex-qdrant docker-reindex-qdrant

setup:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	mypy src

test:
	pytest

run:
	uvicorn sofia_ai_dataops.api.app:create_app --factory --reload

docker-up:
	docker compose up --build

docker-down:
	docker compose down

airflow-lab-up:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml up --build

airflow-lab-down:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml down

reindex-qdrant:
	python -m sofia_ai_dataops.scripts.reindex_qdrant

docker-reindex-qdrant:
	docker compose -f docker-compose.yml -f docker-compose.airflow.yml exec api python -m sofia_ai_dataops.scripts.reindex_qdrant
