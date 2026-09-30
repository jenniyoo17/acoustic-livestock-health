.PHONY: install dev build test migrate seed docker-up docker-down logs

install:
	python -m pip install -r backend/requirements.txt
	python -m pip install -r ml_service/requirements.txt
	python -m pip install -r edge_simulator/requirements.txt
	cd frontend && npm install

dev:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

build:
	cd frontend && npm run build

test:
	cd backend && python -m pytest -q
	cd ml_service && python -m pytest -q
	cd edge_simulator && python -m pytest -q
	cd frontend && npm test -- --run

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.db.seed_postgres

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

logs:
	docker compose logs -f
