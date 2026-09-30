# SIH 2026 - Acoustic Livestock Health Early-Warning System

[![Milestone](https://img.shields.io/badge/Milestone-1%20Completed-brightgreen)](#current-milestone)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An AI-based acoustic early-warning platform for monitoring livestock sound patterns (coughing, distress calls, rumination anomalies) using shed-mounted micro-edge sensors and cloud re-validation.

> **IMPORTANT DISCLAIMER**: This system does **NOT** claim to medically diagnose animals. It identifies statistical acoustic anomalies and generates health-risk alerts that require clinical verification by a registered veterinarian.

---

## Technical Architecture

The monorepo consists of four modular core microservices:

1. **`backend/`**: FastAPI (Python 3.11) with Pydantic v2, SQLAlchemy 2.0 async, PostgreSQL async engine (`asyncpg`).
2. **`frontend/`**: React 18, TypeScript, Vite SPA, Leaflet geospatial mapping.
3. **`ml_service/`**: Python ML microservice for YAMNet feature extraction and TFLite model re-validation.
4. **`edge_simulator/`**: Offline-first Edge AI device simulator with local SQLite storage & store-and-forward batch sync engine.

---

## Current Milestone

### Milestone 1: Monorepo Foundation & Core Infrastructure
- [x] Production monorepo directory layout (`backend`, `frontend`, `ml_service`, `edge_simulator`, `docs`).
- [x] FastAPI async core backend with health status endpoint `GET /health`.
- [x] Async SQLAlchemy 2.0 database session engine.
- [x] React + TypeScript + Vite frontend skeleton.
- [x] Dockerfile configurations & `docker-compose.yml` for local orchestration.
- [x] Makefile with `install`, `dev`, `test`, `build`, `docker-up`, `docker-down`, and `logs` targets.
- [x] Automated backend health check unit tests.

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ / npm 9+
- Docker & Docker Compose (optional for containerized deployment)

### 1. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Local Installation
Install dependencies for all monorepo components:
```bash
make install
```

### 3. Running Development Environment
To launch the backend API server locally:
```bash
make dev
```
Backend API will be live at `http://localhost:8000` (API Docs at `http://localhost:8000/docs`).

To launch the frontend locally:
```bash
cd frontend
npm run dev
```
Frontend will be live at `http://localhost:5173`.

### 4. Running Docker Environment
To spin up all microservices and PostgreSQL container together:
```bash
make docker-up
```

### 5. Running Tests
Run automated tests across backend, ML service, edge simulator, and frontend:
```bash
make test
```

---

## API Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Core system health & service check |
| `GET`  | `/api/v1/health` | API v1 router health status |

---

## License
Distributed under the MIT License for Smart India Hackathon (SIH 2026).
