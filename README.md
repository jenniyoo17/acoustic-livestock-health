# Acoustic Livestock Health Early-Warning System

An offline-first platform for detecting unusual livestock acoustic patterns, including coughs, distress calls, and abnormal rumination. The system is intended to provide early warnings for human review.

> **Medical disclaimer:** Acoustic early-warning anomaly detection only. Veterinary verification required. This system does not diagnose disease.

## Architecture

The planned system connects shed microphones to edge inference, offline storage and synchronization, a FastAPI backend backed by PostgreSQL, alert review workflows, a geospatial dashboard, and government data export. See [docs/architecture.md](docs/architecture.md) and [docs/implementation-plan.md](docs/implementation-plan.md).

This repository currently contains **Milestones 1-6**: the monorepo foundation, PostgreSQL persistence and edge APIs, ML inference with real pretrained YAMNet embeddings plus an untrained demo classifier, timestamp-driven SLA workflow, demo veterinary/lab workflows, and a PostgreSQL-backed tamper-evident audit hash chain. The full dashboard and later milestones are not implemented yet.

## Milestone 6 Audit Ledger

The audit ledger is an append-only SHA-256 hash chain stored in the central PostgreSQL database. It is **not a blockchain**: there is no network, consensus, wallet, smart contract, or external ledger. Block index, timestamp, previous hash, entity type/ID, and payload hash are serialized as compact JSON with sorted keys and UTF-8 encoded before SHA-256 hashing. Payloads use the same canonical JSON rules to produce `payload_hash`; raw workflow payloads are not stored in the ledger.

The deterministic genesis block is index `0`, timestamp `1970-01-01T00:00:00+00:00`, `previous_hash=null`, `entity_type="GENESIS"`, `entity_id="0"`, and payload `{"type":"GENESIS"}`. The first event block references its hash. Unique indexes/hashes/transition keys and a PostgreSQL transaction-scoped advisory lock serialize appends; business writes and audit appends share a transaction. Repeated identical transitions are idempotent. A failed audit append aborts the corresponding workflow transaction rather than falling back to memory.

Audited transitions include alert creation, SLA escalation, acknowledgement, veterinary verification, lab referral creation, and lab referral status changes. The audit ledger records application workflow events; it does not establish medical truth and does not replace veterinary verification.

```sh
curl http://localhost:8000/api/v1/audit/chain
curl -X POST http://localhost:8000/api/v1/audit/verify-integrity
```

Integrity verification checks the unique sequential indexes, single deterministic genesis, previous-hash links, transition keys, and recalculated block hashes. Tampering/deletion is reported as `valid: false` with a block-specific error. The `audit_blocks` table is migration 004 and is included in the PostgreSQL-only deterministic demo seed.

## Milestone 5 Vet and Lab Workflow

`POST /api/v1/vet/verify` accepts an `alert_id`, `outcome` (`Verified_Risk` or `False_Positive`), `vet_identifier`, and `notes`. Verification is allowed only when the alert is `Under_Vet_Review`, after the Milestone 4 acknowledgement flow. Unknown alerts return 404; alerts in another state or already verified return 409. `False_Positive` is recorded and the alert becomes `Resolved`; `Verified_Risk` remains available for a lab referral. These outcomes record a human workflow decision, not a medical diagnosis.

Example vet request:

```json
{"alert_id": "<alert-uuid>", "outcome": "Verified_Risk", "vet_identifier": "DEMO-VET-017", "notes": "Demo assessment; not clinical data."}
```

`POST /api/v1/lab/referrals` accepts `alert_id`, `sample_identifier`, `requested_tests`, and optional `notes`. It only creates one referral for a `Verified_Risk` alert with a saved verification. False-positive, unresolved, or otherwise unverified alerts are rejected. `GET /api/v1/lab/referrals/<referral-id>` returns the referral, alert, and verification.

Lab status updates use `PATCH /api/v1/lab/referrals/<referral-id>/status`. Allowed progression is `Pending` -> `Sample_Collected` -> `In_Lab` -> `Result_Available`, with `Cancelled` available before a result. A manually entered result is required for `Result_Available`; it is prefixed with `DEMO:` and marked `is_demo_result=true`. The service never fabricates a result. Making a result available resolves a Verified_Risk alert; no lab provider is integrated.

The `vet_verifications` and `lab_referrals` PostgreSQL tables are in migration 003 (`make migrate`). Deterministic seed data includes an alert under vet review, a False_Positive example, a Verified_Risk example, and a Verified_Risk with a pending referral. Their notes/sample IDs are demo-only; no clinical results or disease statistics are seeded.

## Milestone 4 Alert SLA Workflow

High/Critical alerts begin at `Tier_1_Farm_Owner` and receive a demo SMS notification. Tier 1 has a 15-minute acknowledgement SLA; if it expires, the alert advances to `Tier_2_Field_Vet` with a demo SMS. Tier 2 has a 45-minute acknowledgement SLA; if it expires, the alert advances to `Tier_3_District_Officer` with a demo voice notification. Lower severities do not run SLA escalation.

The alert state transitions use the existing statuses: `Pending_Triage` -> `Escalated` -> `Under_Vet_Review` -> `Verified_Risk` or `False_Positive` -> `Resolved`. A Tier 1 acknowledgement advances the alert to `Under_Vet_Review` and starts Tier 2 review. Acknowledgements require the current tier and a repeated/stale tier returns HTTP 409. This demo milestone does not expose an API to mark an alert verified or false positive; no escalation code can assert a disease outcome.

The `escalation_records` PostgreSQL table records each tier's trigger, acknowledgement, reason, and timestamps. Apply migrations with `make migrate`. Acknowledging an alert is:

```sh
curl -X POST http://localhost:8000/api/v1/alerts/<alert-id>/acknowledge \
	-H "Content-Type: application/json" \
	-d '{"tier":"Tier_1_Farm_Owner"}'
```

Use `GET /api/v1/alerts/escalation-status` for dashboard-ready current deadlines and history, or `GET /api/v1/alerts/<alert-id>` for alert/event/shed/device detail. Both GET endpoints accept an optional ISO timestamp `at` for viewing state at a simulated time; GET does not mutate alerts. To actually process due notifications, call the evaluator with demo time:

```sh
curl -X POST 'http://localhost:8000/api/v1/alerts/escalations/evaluate?at=2026-09-30T12:16:00Z'
```

For a seeded/test alert triggered at `12:00Z`, evaluating at `12:16Z` escalates to Tier 2 immediately. Evaluating again at `13:01Z` breaches Tier 2's 45-minute window from its Tier 2 notification time. No sleeps or background escalation loop are used.

SMS and voice adapters are mock-only: they log and retain the recipient, notification type, alert ID, message, and timestamp in process memory. No real provider is contacted. Message language remains “Acoustic anomaly detected” and “Veterinary verification required.”

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
