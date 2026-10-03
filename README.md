# Acoustic Livestock Health Early-Warning System

An offline-first demo platform for monitoring livestock acoustic patterns such as coughs, distress calls, and abnormal rumination. The system is designed to surface early warnings for human review in a controlled operational workflow.

> Medical boundary: "Acoustic Early-Warning & Anomaly Detection only." Veterinary clinical verification remains mandatory. The system does not diagnose disease or prescribe treatment.

## 1. Project Overview

This repository implements the SIH 2026 acoustic livestock health early-warning workflow across four services:

- Backend: FastAPI + PostgreSQL data model for alerts, SLA, vet/lab workflows, and audit logging
- Edge simulator: SQLite-backed local queue with offline buffering, signing, retry, batching, and sync
- ML service: YAMNet embedding pipeline and demo classifier
- Frontend: React + TypeScript + Vite dashboard for command center, alerts, vet/lab, audit, and export views

The system is a demonstration environment, not a production clinical or government system.

## 2. Problem Being Addressed

The project models a livestock monitoring operation where edge microphones generate acoustic events, the local device keeps a queue when connectivity is poor, and the central backend resolves escalation, review, and compliance evidence. The practical problem is ensuring the offline-first pipeline, alert workflow, and proof trail work reliably without inventing fake integrations.

## 3. Solution

The repository contains a full demo stack that:

- captures edge events locally when the backend is unreachable
- batches signed events up to 50 per request and verifies batch hashes
- ingests events into the central backend PostgreSQL pipeline
- creates alert + SLA escalation states
- supports acknowledgement, vet review, and lab referral workflows
- records a tamper-evident SHA-256 audit ledger
- exposes a React dashboard that reads the real backend contract

## 4. Architecture

```text
Edge device / simulator
  ↓
Local SQLite queue
  ↓
Signed batch sync
  ↓
FastAPI backend (PostgreSQL)
  ↓
Acoustic event -> alert -> SLA -> vet/lab workflow
  ↓
Tamper-evident SHA-256 audit ledger
  ↓
React dashboard and export views
```

The backend remains PostgreSQL-backed; SQLite is used only in the edge simulator queue. The system is intentionally offline-first and delay-tolerant, but not medical-grade.

## 5. Technology Stack

- Python 3.11
- FastAPI
- SQLAlchemy async + PostgreSQL
- Alembic migrations
- SQLite for edge-local queue only
- React + TypeScript + Vite
- Vitest + Testing Library
- YAMNet embedding pipeline + demo classifier

## 6. M1-M9 Implementation Summary

Implemented milestones include:

- M1: monorepo foundation and service layout
- M2: PostgreSQL schema and backend persistence
- M3: ML feature pipeline and demo classifier
- M4: alert + SLA escalation workflow
- M5: veterinary verification + lab referral workflow
- M6: tamper-evident SHA-256 audit ledger
- M7: edge simulator offline queue, batching, retry, and sync
- M8: React dashboard using the backend API contract
- M9: final verification and documentation package

## 7. How to Run the Backend

From the repo root:

```sh
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Health check:

```sh
curl http://localhost:8000/health
```

## 8. How to Run the ML Service

```sh
cd ml_service
python -m uvicorn src.main:app --reload --port 8001
```

Example prediction request:

```sh
python -m src.demo_audio Coughing_Spike demo-cough.wav
curl -F "audio=@demo-cough.wav;type=audio/wav" http://localhost:8001/predict
```

The ML classifier remains an untrained demo classifier. It does not claim livestock medical accuracy.

## 9. How to Run the Edge Simulator

```sh
cd edge_simulator
python -m uvicorn src.main:app --reload --port 8002
```

CLI examples:

```sh
cd edge_simulator
python cli.py status
python cli.py generate --count 3 --event-type Cough --confidence 0.91
python cli.py queue
python cli.py sync
python cli.py heartbeat
```

The simulator stores local queued events in SQLite, retries when the backend is unavailable, and enforces the backend max batch size of 50.

## 10. How to Run the Frontend

```sh
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

Open the dashboard in the browser and use the command center, alerts board, vet/lab workflow, audit ledger, and export pages.

## 11. Demo Workflow

The intended end-to-end flow is:

1. Start backend, ML service, edge simulator, and frontend.
2. Generate an event from the edge simulator.
3. Observe the event in the local SQLite queue while offline or during a sync retry.
4. Sync the queue to the backend.
5. Confirm incoming acoustic event and alert creation.
6. Review escalating SLA state.
7. Acknowledge the alert.
8. Run vet verification.
9. Create a lab referral.
10. Update lab status.
11. Open the audit ledger and verify integrity.
12. Review the dashboard and export states.

## 12. API Overview

The major backend endpoints are:

- `POST /api/v1/edge/ingest`
- `POST /api/v1/edge/sync-batch`
- `POST /api/v1/edge/heartbeat`
- `GET /api/v1/alerts/escalation-status`
- `GET /api/v1/alerts/{alert_id}`
- `POST /api/v1/alerts/{alert_id}/acknowledge`
- `POST /api/v1/vet/verify`
- `POST /api/v1/lab/referrals`
- `GET /api/v1/lab/referrals/{referral_id}`
- `PATCH /api/v1/lab/referrals/{referral_id}/status`
- `GET /api/v1/audit/chain`
- `POST /api/v1/audit/verify-integrity`
- `GET /api/v1/geo/outbreak-clusters`
- `GET /api/v1/export/government-nadrs`

## 13. Offline-First Behavior

The edge simulator is intentionally local-first. Events are queued in SQLite until the backend is reachable, then they are synced as signed batches with a strict maximum batch size of 50. Failed sync attempts remain UNSYNCED with the last error recorded, and successful sync marks the queue as ACKNOWLEDGED or de-duplicates identical events.

## 14. Audit Ledger

The backend includes a tamper-evident SHA-256 audit ledger. It is not a blockchain, token, or production ledger system. It stores sequential, linked, append-only workflow hashes and exposes integrity verification for the existing workflow events.

## 15. Medical Boundary

The project must remain within a clearly stated medical boundary:

- Acoustic early warning and anomaly detection only
- veterinary verification required
- no automated disease diagnosis
- no automated treatment recommendations
- no clinical certainty inferred from acoustic alone

## 16. Current Limitations

- The project is a demo and not production deployment software.
- Real PostgreSQL and Docker were not live-verified in this environment.
- The ML classifier is demo-only and intentionally not clinically trained.
- Government export and geospatial endpoints are exposed only when the current backend implements them; the frontend shows the real response state instead of fabricating data.
- This repository is designed for demo workflows and validation, not field deployment.

## 17. Testing Status

Current verified status in this workspace:

- Backend: 67 passed
- Edge simulator: 13 passed
- ML service: 18 passed, 1 skipped
- Frontend: 4 passed
- Frontend build: PASS
- TypeScript build: PASS
- Migration SQL rendering: PASS for PostgreSQL form via Alembic SQL generation

Live PostgreSQL/Docker migration execution is not claimed here because PostgreSQL/Docker was unavailable in the current environment.
