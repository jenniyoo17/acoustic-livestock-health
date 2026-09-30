# Acoustic Livestock Health Early-Warning System

An offline-first platform for detecting unusual livestock acoustic patterns, including coughs, distress calls, and abnormal rumination. The system is intended to provide early warnings for human review.

> **Medical disclaimer:** Acoustic early-warning anomaly detection only. Veterinary verification required. This system does not diagnose disease.

## Architecture

The planned system connects shed microphones to edge inference, offline storage and synchronization, a FastAPI backend backed by PostgreSQL, alert review workflows, a geospatial dashboard, and government data export. See [docs/architecture.md](docs/architecture.md) and [docs/implementation-plan.md](docs/implementation-plan.md).

This repository currently contains **Milestone 1 only**: service health endpoints, PostgreSQL connection/session infrastructure, a minimal frontend, and local orchestration. Later architecture components are not implemented yet.

## Technology Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 async, asyncpg
- ML and edge placeholders: lightweight FastAPI services
- Frontend: React, TypeScript, Vite
- Local orchestration: Docker Compose and PostgreSQL 16
- Tests: pytest, HTTPX, Vitest, and Testing Library

## Repository Structure

```text
backend/         FastAPI health endpoint and async DB session infrastructure
ml_service/      ML service health placeholder
edge_simulator/  Edge service health placeholder
frontend/        Minimal React application
docs/            Architecture and approved milestone plan
```

## Setup

Requirements: Python 3.11+, Node.js with npm, and optionally Docker Compose.

Copy `.env.example` to `.env` and replace the development database password if needed. Install dependencies with:

```sh
make install
```

Start the backend locally from the repository root:

```sh
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

Start the ML service and edge placeholder in separate terminals:

```sh
cd ml_service && python -m uvicorn src.main:app --reload --port 8001
cd edge_simulator && python -m uvicorn src.main:app --reload --port 8002
```

Start the frontend with `cd frontend && npm run dev -- --host 0.0.0.0 --port 3000`.

Health endpoints are `http://localhost:8000/health`, `http://localhost:8001/health`, and `http://localhost:8002/health`.

## Tests and Build

Run all lightweight unit tests with `make test`; build the frontend with `make build`. Tests do not require Docker, external APIs, or downloaded models.

## Docker

Copy `.env.example` to `.env`, then run:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose down
```

The backend waits for PostgreSQL's `pg_isready` healthcheck. No migrations or application tables are part of Milestone 1.
