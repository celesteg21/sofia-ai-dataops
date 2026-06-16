.PHONY: setup lint test run docker-up docker-down

setup:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	mypy app

test:
	pytest

run:
	uvicorn app.main:app --reload

docker-up:
	docker compose up --build

docker-down:
	docker compose down
