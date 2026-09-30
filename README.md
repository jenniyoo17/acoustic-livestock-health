# Acoustic Livestock Health Early-Warning System

An offline-first platform for detecting unusual livestock acoustic patterns, including coughs, distress calls, and abnormal rumination. The system is intended to provide early warnings for human review.

> **Medical disclaimer:** Acoustic early-warning anomaly detection only. Veterinary verification required. This system does not diagnose disease.

## Architecture

The planned system connects shed microphones to edge inference, offline storage and synchronization, a FastAPI backend backed by PostgreSQL, alert review workflows, a geospatial dashboard, and government data export. See [docs/architecture.md](docs/architecture.md) and [docs/implementation-plan.md](docs/implementation-plan.md).

This repository currently contains **Milestones 1, 2, and 3**: the monorepo foundation, PostgreSQL persistence and edge APIs, and an ML inference pipeline with real pretrained YAMNet embeddings plus an untrained demo classifier. Later workflows and the full dashboard are not implemented yet.

## Milestone 3 ML Pipeline

`POST /predict` accepts an uploaded WAV/audio file. The ML service decodes it, converts multichannel audio to mono, resamples to 16 kHz, peak-normalizes finite float32 samples, then extracts real pretrained YAMNet frame embeddings and averages them into a 1024-value vector. The YAMNet model is loaded lazily on the first prediction and reused for subsequent requests. If TensorFlow, TensorFlow Hub, or the model is unavailable, `/predict` returns HTTP 503; it does not substitute fake YAMNet features.

The classifier is deliberately a deterministic, untrained demo MLP with Dense 256, Dense 64, and four-way Softmax layers. Its output classes are `Normal_Rumination`, `Coughing_Spike`, `Distress_Vocal`, and `Ambient_Noise`. Every response marks `classifier_status` as `UNTRAINED_DEMO`; its class and confidence are not calibrated, are not livestock accuracy measurements, and must not be used as health or clinical conclusions. No labeled livestock training data or accuracy claim is included.

Run the ML service and create a synthetic demo WAV from the `ml_service/` directory:

```sh
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
python -m src.demo_audio Coughing_Spike demo-cough.wav
curl -F "audio=@demo-cough.wav;type=audio/wav" http://localhost:8001/predict
```

The generated audio is a small deterministic demonstration signal, not a recording of livestock. `/predict` responds with `predicted_class`, `confidence`, `classifier_status`, `embedding_dimension`, `processing_time_ms`, and `model_version`, for example:

```json
{"predicted_class": "Ambient_Noise", "confidence": 0.41, "classifier_status": "UNTRAINED_DEMO", "embedding_dimension": 1024, "processing_time_ms": 31.2, "model_version": "demo-yamnet-v1"}
```

Run the fast ML unit suite with `cd ml_service && python -m pytest -q`; it uses fake feature extraction and does not download/load YAMNet. The separate real-model integration test is opt-in: set `RUN_YAMNET_INTEGRATION=1` before running `python -m pytest -q tests/test_yamnet_integration.py` (in PowerShell, use `$env:RUN_YAMNET_INTEGRATION='1'`). Export the demo-only classifier to FP16 TFLite with `python -m src.export_tflite demo-classifier.tflite`. Model files and generated `ml_service/demo-*.wav` files are ignored by Git.

Measured on the current Windows CPU environment with a synthetic 0.96-second sample: warm YAMNet feature extraction measured 22.52-45.55 ms across three calls; warm `/predict` measured 31.2 ms. The first `/predict` in a fresh process measured 23,420 ms including model initialization. These are local observations, not a latency guarantee. The real YAMNet model returned an embedding of shape `(1024,)`; the untrained head predicted `Ambient_Noise` for a synthetic cough signal, illustrating why its results have no classifier accuracy meaning. This remains an acoustic early-warning/anomaly prototype, not automated diagnosis.

## Milestone 2 Database

The PostgreSQL schema contains `farms`, `sheds`, `devices`, `acoustic_events`, and `alerts`. Farms own sheds; sheds own devices and reference events/alerts; devices own acoustic events; each alert refers to an event and shed. Event embeddings are stored as JSON. Database constraints enforce enum values, capacity bounds, confidence range, positive duration, and unique device IDs/event idempotency keys.

Set `DATABASE_URL` and `DEVICE_HMAC_SECRET` in `.env`. The central backend requires PostgreSQL; there is no SQLite fallback. Run the migration and deterministic seed from the repository root:

```sh
make migrate
make seed
```

Seed records have fixed IDs and can be applied repeatedly after migration. The seed command never creates tables and never changes to a fallback database.

## Edge API

`POST /api/v1/edge/ingest` stores one event and creates a basic pending alert for non-background events with confidence of at least `0.65`. `POST /api/v1/edge/sync-batch` accepts 1-50 events, validates a canonical SHA-256 batch digest, and reports accepted, duplicate, and rejected records. `POST /api/v1/edge/heartbeat` updates the registered device's status and server heartbeat timestamp.

An event signature is HMAC-SHA256 using `DEVICE_HMAC_SECRET` and compact, key-sorted JSON of the event fields except `signature`. The batch digest is SHA-256 over compact, key-sorted JSON of the `events` array, including each event signature. Device signatures are a lightweight shared-secret development mechanism, not production PKI.

Example request shapes:

```json
{
	"device_uid": "MIC-DEMO-ANAND-01",
	"timestamp": 1780000000.0,
	"event_type": "Cough",
	"confidence": 0.89,
	"duration_sec": 2.4,
	"embedding": [0.01, -0.02],
	"signature": "<64-character HMAC-SHA256 hex digest>"
}
```

The batch body contains `events` in that shape and `batch_hash` set to the 64-character SHA-256 hex digest of the canonicalized event list. Example batch body:

```json
{"events": [{"device_uid": "MIC-DEMO-ANAND-01", "timestamp": 1780000000.0, "event_type": "Cough", "confidence": 0.89, "duration_sec": 2.4, "embedding": [0.01, -0.02], "signature": "<64-character HMAC-SHA256 hex digest>"}], "batch_hash": "<64-character SHA-256 hex digest>"}
```

A successful ingest returns a response like:

```json
{"accepted": true, "event_id": "<uuid>", "device_uid": "MIC-DEMO-ANAND-01", "status": "stored", "alert_created": true, "alert_id": "<uuid>"}
```

A batch response includes `accepted`, `duplicates`, `rejected`, and per-event results, for example `{"accepted": 1, "duplicates": 0, "rejected": 0, "results": [{"index": 0, "device_uid": "MIC-DEMO-ANAND-01", "accepted": true, "status": "stored", "event_id": "<uuid>"}]}`. Heartbeat accepts `device_uid`, optional `firmware_version`, and `status` (`Online`, `Offline`, or `Degraded`), for example:

```json
{"device_uid": "MIC-DEMO-ANAND-01", "firmware_version": "0.1.0", "status": "Online"}
```

The heartbeat response contains `acknowledged`, the device UID/status, and a server timestamp in `last_heartbeat_at`.

The backend OpenAPI page at `http://localhost:8000/docs` provides the request/response schemas.

## Technology Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 async, asyncpg
- ML and edge placeholders: lightweight FastAPI services
- Frontend: React, TypeScript, Vite
- Local orchestration: Docker Compose and PostgreSQL 16
- Tests: pytest, HTTPX, and Vitest with React static rendering

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

Copy `.env.example` to `.env` and replace the development-only database password and HMAC secret before deployment. Install dependencies with:

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

Run all lightweight tests with `make test`; build the frontend with `make build`. Backend API/model tests use a deterministic in-memory session double and do not require Docker or SQLite. Alembic can render PostgreSQL migration SQL offline with `cd backend && alembic upgrade head --sql`; live migration and seed execution require PostgreSQL.

## Docker

Copy `.env.example` to `.env`, then run:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose down
```

The backend waits for PostgreSQL's `pg_isready` healthcheck. After starting Compose, run `make migrate` and `make seed` from the repository root.
