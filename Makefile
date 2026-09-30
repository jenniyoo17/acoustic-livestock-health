.PHONY: install dev build test docker-up docker-down logs help

help:
	@echo "SIH 2026 - Acoustic Livestock Health Early-Warning System"
	@echo "Available commands:"
	@echo "  make install     - Install all local dependencies"
	@echo "  make dev         - Run development servers"
	@echo "  make test        - Run tests across all services"
	@echo "  make build       - Build production artifacts"
	@echo "  make docker-up   - Start services via docker-compose"
	@echo "  make docker-down - Stop docker-compose services"
	@echo "  make logs        - Tail docker-compose logs"

install:
	cd backend && python -m pip install -r requirements.txt
	cd ml_service && python -m pip install -r requirements.txt
	cd edge_simulator && python -m pip install -r requirements.txt
	cd frontend && npm install

dev:
	@echo "Starting development environment..."
	cd backend && python -m uvicorn app.main:app --reload --port 8000

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest
	@echo "Running ML service tests..."
	cd ml_service && python -m pytest
	@echo "Running edge simulator tests..."
	cd edge_simulator && python -m pytest
	@echo "Running frontend tests..."
	cd frontend && npm test -- --run

build:
	cd frontend && npm run build

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down

logs:
	docker-compose logs -f
